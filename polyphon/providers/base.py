"""Abstract base class for all TTS providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SynthesisResult:
    """Result returned by every TTS provider."""

    audio: bytes
    provider: str
    voice: str
    characters: int
    duration_ms: float        # generation latency (API call time)
    audio_duration_s: float   # actual length of the audio clip
    file_size_bytes: int      # MP3 size in bytes
    cost_usd: float           # estimated cost for this chunk


class TTSProvider(ABC):
    """Abstract TTS provider. All providers must implement this interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'google', 'elevenlabs')."""

    @property
    @abstractmethod
    def voice(self) -> str:
        """Current voice identifier."""

    @property
    @abstractmethod
    def cost_per_million_chars(self) -> float:
        """Cost in USD per 1,000,000 characters."""

    def estimate_cost(self, characters: int) -> float:
        """Calculate cost for a given number of characters."""
        return (characters / 1_000_000) * self.cost_per_million_chars

    @abstractmethod
    def synthesize(self, text: str) -> SynthesisResult:
        """
        Convert text to MP3 audio bytes.

        Args:
            text: Plain text to synthesize.

        Returns:
            SynthesisResult with audio bytes and metadata.
        """
