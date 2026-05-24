"""Polyphon — pluggable text-to-speech pipeline for audiobook generation."""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "Pipeline",
    "TTSProvider",
    "SynthesisResult",
    "GoogleTTSProvider",
    "ElevenLabsProvider",
    "AzureTTSProvider",
    "KokoroProvider",
]


def __getattr__(name: str) -> object:
    """Lazy-load providers so missing optional dependencies don't break imports."""
    if name == "Pipeline":
        from polyphon.core.pipeline import Pipeline
        return Pipeline
    if name == "TTSProvider":
        from polyphon.providers.base import TTSProvider
        return TTSProvider
    if name == "SynthesisResult":
        from polyphon.providers.base import SynthesisResult
        return SynthesisResult
    if name == "GoogleTTSProvider":
        from polyphon.providers.google import GoogleTTSProvider
        return GoogleTTSProvider
    if name == "ElevenLabsProvider":
        from polyphon.providers.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider
    if name == "AzureTTSProvider":
        from polyphon.providers.azure import AzureTTSProvider
        return AzureTTSProvider
    if name == "KokoroProvider":
        from polyphon.providers.kokoro import KokoroProvider
        return KokoroProvider
    raise AttributeError(f"module 'polyphon' has no attribute {name!r}")
