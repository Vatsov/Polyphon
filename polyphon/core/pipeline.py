"""Main pipeline orchestrator — ties chunker, provider, state and audio together."""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn

from polyphon.core.audio import add_silence, concat_mp3s
from polyphon.core.chunker import chunk_text
from polyphon.core.state import PipelineState
from polyphon.metrics.collector import MetricsCollector
from polyphon.metrics.db import MetricsDB
from polyphon.providers.base import TTSProvider

console = Console()


class Pipeline:
    """
    Orchestrates text-to-speech conversion for a full document.

    - Splits input text into chunks
    - Synthesizes each chunk via the given TTSProvider
    - Tracks progress (resumable on crash)
    - Records metrics for every synthesis call (JSON + SQLite)
    - Concatenates chunks into a final MP3

    Usage::

        provider = GoogleTTSProvider(voice_name="bg-BG-Chirp3-HD-Aoede")
        pipeline = Pipeline(provider=provider, output_dir=Path("output"))
        pipeline.run(text=Path("book.txt").read_text(), output_name="my_book")
    """

    def __init__(
        self,
        provider: TTSProvider,
        output_dir: Path,
        silence_ms: int = 500,
        max_chunk_chars: int = 500,
        limit: Optional[int] = None,
        db_path: Path = Path("polyphon_metrics.db"),
    ) -> None:
        self._provider = provider
        self._output_dir = output_dir
        self._silence_ms = silence_ms
        self._max_chunk_chars = max_chunk_chars
        self._limit = limit
        self._metrics = MetricsCollector()
        self._db = MetricsDB(db_path)
        output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, text: str, output_name: str = "output") -> Path:
        """
        Convert text to a single MP3 audiobook file.

        Args:
            text:        Full plain text to synthesize.
            output_name: Base name for the output file (no extension).

        Returns:
            Path to the final MP3 file.
        """
        chunks = chunk_text(text, max_chars=self._max_chunk_chars)
        if self._limit:
            chunks = chunks[: self._limit]

        chunks_dir = self._output_dir / f"{output_name}_chunks"
        chunks_dir.mkdir(exist_ok=True)

        state = PipelineState(self._output_dir / f"{output_name}_state.json")
        state.init(total_chunks=len(chunks))

        chunk_files: list[Path] = []
        errors = 0

        with Progress(
            TextColumn("[purple]{task.description}[/purple]"),
            BarColumn(bar_width=40),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Synthesizing", total=len(chunks))

            for index, chunk in enumerate(chunks):
                chunk_path = chunks_dir / f"{index:05d}.mp3"
                chunk_files.append(chunk_path)

                if state.is_completed(index):
                    progress.advance(task)
                    continue

                try:
                    result = self._provider.synthesize(chunk)
                    audio = add_silence(result.audio, self._silence_ms)
                    chunk_path.write_bytes(audio)

                    self._metrics.record(result)
                    self._db.insert(result, job=output_name, success=True, silence_ms=self._silence_ms)
                    state.mark_completed(index)

                except Exception as exc:  # noqa: BLE001
                    console.print(f"[red]  ✗ chunk {index}:[/red] {exc}")
                    self._db.insert_failure(
                        provider=self._provider.name,
                        voice=self._provider.voice,
                        characters=len(chunk),
                        job=output_name,
                    )
                    state.mark_failed(index)
                    errors += 1

                progress.advance(task)

        output_path = self._output_dir / f"{output_name}.mp3"
        console.print(f"\n[dim]Concatenating {len(chunk_files)} chunks…[/dim]")
        concat_mp3s(chunk_files, output_path)

        self._metrics.save(self._output_dir / f"{output_name}_metrics.json")
        self._db.close()

        summary = self._metrics.summary()
        console.print(
            f"[green]✓[/green] {len(chunks) - errors}/{len(chunks)} chunks  "
            f"· {summary.get('total_characters', 0):,} chars  "
            f"· avg {summary.get('avg_ms_per_chunk', 0):.0f}ms/chunk"
        )

        return output_path
