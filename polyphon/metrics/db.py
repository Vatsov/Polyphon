"""SQLite persistence for metrics — feeds the dashboard."""

import sqlite3
import time
from pathlib import Path

from polyphon.providers.base import SynthesisResult

_SCHEMA = """
CREATE TABLE IF NOT EXISTS synthesis (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ts               REAL    NOT NULL,
    job              TEXT    NOT NULL DEFAULT '',
    provider         TEXT    NOT NULL,
    voice            TEXT    NOT NULL,
    characters       INTEGER NOT NULL,
    duration_ms      REAL    NOT NULL,
    audio_duration_s REAL    NOT NULL DEFAULT 0,
    file_size_bytes  INTEGER NOT NULL DEFAULT 0,
    cost_usd         REAL    NOT NULL DEFAULT 0,
    success          INTEGER NOT NULL DEFAULT 1,
    silence_ms       INTEGER NOT NULL DEFAULT 500
);
"""


class MetricsDB:
    """Write synthesis results to SQLite for dashboard queries."""

    def __init__(self, db_path: Path = Path("polyphon_metrics.db")) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def insert(
        self,
        result: SynthesisResult,
        job: str = "",
        success: bool = True,
        silence_ms: int = 500,
    ) -> None:
        self._conn.execute(
            """INSERT INTO synthesis
               (ts, job, provider, voice, characters, duration_ms,
                audio_duration_s, file_size_bytes, cost_usd, success, silence_ms)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                time.time(),
                job,
                result.provider,
                result.voice,
                result.characters,
                result.duration_ms,
                result.audio_duration_s,
                result.file_size_bytes,
                result.cost_usd,
                1 if success else 0,
                silence_ms,
            ),
        )
        self._conn.commit()

    def insert_failure(self, provider: str, voice: str, characters: int, job: str = "") -> None:
        """Record a failed synthesis attempt."""
        self._conn.execute(
            """INSERT INTO synthesis
               (ts, job, provider, voice, characters, duration_ms,
                audio_duration_s, file_size_bytes, cost_usd, success, silence_ms)
               VALUES (?,?,?,?,?,0,0,0,0,0,0)""",
            (time.time(), job, provider, voice, characters),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
