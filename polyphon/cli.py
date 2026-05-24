"""Polyphon CLI — convert text to audiobook with one command."""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()

app = typer.Typer(
    name="polyphon",
    help="Pluggable TTS pipeline for audiobook generation.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


class Provider(str, Enum):
    google = "google"
    elevenlabs = "elevenlabs"
    azure = "azure"
    kokoro = "kokoro"


# ── convert ───────────────────────────────────────────────────────────────────

@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Path to the plain-text file to convert."),
    provider: Provider = typer.Option(Provider.google, "--provider", "-p", help="TTS provider to use."),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Voice name (provider-specific). Uses default if omitted."),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output base name (default: input filename without extension)."),
    output_dir: Path = typer.Option(Path("output"), "--output-dir", help="Directory for generated files."),
    silence_ms: int = typer.Option(500, "--silence-ms", help="Silence between sentences in milliseconds."),
    limit: Optional[int] = typer.Option(None, "--limit", help="Process only the first N chunks (for testing)."),
    dashboard: bool = typer.Option(False, "--dashboard", "-d", help="Launch the metrics dashboard after conversion."),
) -> None:
    """
    Convert a text file to an MP3 audiobook.

    \b
    Examples:
      polyphon book.txt
      polyphon book.txt --provider elevenlabs --voice "Rachel"
      polyphon book.txt --provider google --voice bg-BG-Chirp3-HD-Aoede
      polyphon book.txt --limit 5   # quick test with 5 chunks
    """
    from polyphon.core.pipeline import Pipeline

    if not input_file.exists():
        console.print(f"[red]✗ File not found:[/red] {input_file}")
        raise typer.Exit(1)

    tts_provider = _build_provider(provider, voice)
    output_name = output or input_file.stem

    console.print(Panel(
        f"[bold]Provider:[/bold] {provider.value}\n"
        f"[bold]Voice:[/bold]    {tts_provider.voice}\n"
        f"[bold]Input:[/bold]    {input_file}\n"
        f"[bold]Output:[/bold]   {output_dir / output_name}.mp3",
        title="[purple]🎙 Polyphon[/purple]",
        border_style="purple",
    ))

    pipeline = Pipeline(
        provider=tts_provider,
        output_dir=output_dir,
        silence_ms=silence_ms,
        max_chunk_chars=500,
        limit=limit,
    )

    text = input_file.read_text(encoding="utf-8")
    result_path = pipeline.run(text=text, output_name=output_name)

    console.print(f"\n[green]✓ Done:[/green] {result_path}")

    if dashboard:
        _start_dashboard()


# ── dashboard ─────────────────────────────────────────────────────────────────

@app.command()
def dashboard(
    port: int = typer.Option(8765, "--port", help="Port to serve the dashboard on."),
) -> None:
    """Launch the metrics dashboard in the browser."""
    _start_dashboard(port=port)


# ── providers ─────────────────────────────────────────────────────────────────

@app.command()
def providers() -> None:
    """List all available TTS providers and their default Bulgarian voices."""
    table = Table(title="Available Providers", border_style="purple")
    table.add_column("Provider", style="bold")
    table.add_column("Default BG Voice")
    table.add_column("Env Var Required")
    table.add_column("Status")

    rows = [
        ("google",     "bg-BG-Chirp3-HD-Aoede", "GOOGLE_APPLICATION_CREDENTIALS", _check_env("GOOGLE_APPLICATION_CREDENTIALS")),
        ("elevenlabs", "multilingual_v2",         "ELEVENLABS_API_KEY",            _check_env("ELEVENLABS_API_KEY")),
        ("azure",      "bg-BG-KalinaNeural",      "AZURE_SPEECH_KEY + AZURE_SPEECH_REGION", _check_env("AZURE_SPEECH_KEY")),
        ("kokoro",     "af_bella (no BG support)", "—",                            "⚪ offline"),
    ]

    for name, voice, env, status in rows:
        table.add_row(name, voice, env, status)

    console.print(table)


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_provider(provider: Provider, voice: Optional[str]):  # type: ignore[return]
    if provider == Provider.google:
        from polyphon.providers.google import GoogleTTSProvider
        return GoogleTTSProvider(voice_name=voice or "bg-BG-Chirp3-HD-Aoede")

    if provider == Provider.elevenlabs:
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            console.print("[red]✗ ELEVENLABS_API_KEY not set. Add it to .env[/red]")
            raise typer.Exit(1)
        from polyphon.providers.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider(api_key=api_key, voice_id=voice or "21m00Tcm4TlvDq8ikWAM")

    if provider == Provider.azure:
        key = os.environ.get("AZURE_SPEECH_KEY", "")
        region = os.environ.get("AZURE_SPEECH_REGION", "")
        if not key or not region:
            console.print("[red]✗ AZURE_SPEECH_KEY or AZURE_SPEECH_REGION not set. Add them to .env[/red]")
            raise typer.Exit(1)
        from polyphon.providers.azure import AzureTTSProvider
        return AzureTTSProvider(subscription_key=key, region=region, voice_name=voice or "bg-BG-KalinaNeural")

    if provider == Provider.kokoro:
        from polyphon.providers.kokoro import KokoroProvider
        return KokoroProvider(voice=voice or "af_bella")


def _check_env(key: str) -> str:
    return "[green]✓ set[/green]" if os.environ.get(key) else "[yellow]⚠ missing[/yellow]"


def _start_dashboard(port: int = 8765) -> None:
    import webbrowser
    from polyphon.dashboard.server import serve
    webbrowser.open(f"http://127.0.0.1:{port}")
    serve(port=port)
