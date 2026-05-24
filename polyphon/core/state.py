"""Resumable state management — tracks which chunks are already synthesized."""

import json
from pathlib import Path


class PipelineState:
    """
    Persists synthesis progress to disk so a run can be resumed after a crash.

    State file format (JSON):
        {
            "total": 142,
            "completed": [0, 1, 2, ...],
            "failed": [7, 23, ...]
        }
    """

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._data: dict = {"total": 0, "completed": [], "failed": []}
        if state_path.exists():
            self._data = json.loads(state_path.read_text())

    def init(self, total_chunks: int) -> None:
        """Initialize state for a new run (no-op if already initialized)."""
        if self._data["total"] == 0:
            self._data["total"] = total_chunks
            self._save()

    def is_completed(self, index: int) -> bool:
        return index in self._data["completed"]

    def mark_completed(self, index: int) -> None:
        if index not in self._data["completed"]:
            self._data["completed"].append(index)
            self._save()

    def mark_failed(self, index: int) -> None:
        if index not in self._data["failed"]:
            self._data["failed"].append(index)
            self._save()

    @property
    def completed_count(self) -> int:
        return len(self._data["completed"])

    @property
    def total(self) -> int:
        return self._data["total"]

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))
