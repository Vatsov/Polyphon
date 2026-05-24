"""Collect and persist synthesis metrics."""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from polyphon.providers.base import SynthesisResult


@dataclass
class MetricEntry:
    provider: str
    voice: str
    characters: int
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Accumulates SynthesisResult entries and writes them to JSON."""

    def __init__(self) -> None:
        self._entries: list[MetricEntry] = []

    def record(self, result: SynthesisResult) -> None:
        self._entries.append(
            MetricEntry(
                provider=result.provider,
                voice=result.voice,
                characters=result.characters,
                duration_ms=result.duration_ms,
            )
        )

    def summary(self) -> dict:
        if not self._entries:
            return {}
        total_chars = sum(e.characters for e in self._entries)
        total_ms = sum(e.duration_ms for e in self._entries)
        return {
            "total_chunks": len(self._entries),
            "total_characters": total_chars,
            "total_duration_ms": total_ms,
            "avg_ms_per_chunk": total_ms / len(self._entries),
            "chars_per_second": total_chars / (total_ms / 1000) if total_ms else 0,
        }

    def save(self, path: Path) -> None:
        data = {
            "summary": self.summary(),
            "entries": [asdict(e) for e in self._entries],
        }
        path.write_text(json.dumps(data, indent=2))
