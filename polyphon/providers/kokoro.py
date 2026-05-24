"""Kokoro-82M local TTS provider (offline, no Bulgarian support)."""

import io
import time

import numpy as np
import soundfile as sf  # type: ignore[import]
from kokoro import KPipeline  # type: ignore[import]

from polyphon.core.audio import get_audio_duration
from polyphon.providers.base import SynthesisResult, TTSProvider

# NOTE: Kokoro-82M does NOT support Bulgarian.
# Supported lang codes: a=en-US, b=en-GB, j=ja, z=zh, e=es, f=fr, h=hi, i=it, p=pt
# This provider is included for completeness and non-Bulgarian use cases.


class KokoroProvider(TTSProvider):
    """
    Kokoro-82M local TTS provider.

    Runs fully offline. Requires a GPU for real-time performance.
    Does NOT support Bulgarian — use GoogleTTSProvider for bg-BG.
    """

    def __init__(self, lang_code: str = "a", voice: str = "af_bella", device: str = "cpu") -> None:
        self._lang_code = lang_code
        self._voice_name = voice
        self._pipe = KPipeline(lang_code=lang_code, device=device)

    @property
    def name(self) -> str:
        return "kokoro"

    @property
    def voice(self) -> str:
        return self._voice_name

    @property
    def cost_per_million_chars(self) -> float:
        return 0.0  # local model, no API cost

    def synthesize(self, text: str) -> SynthesisResult:
        started = time.monotonic()

        parts = [
            np.asarray(audio, dtype=np.float32)
            for _, _, audio in self._pipe(text, voice=self._voice_name)
        ]
        audio_np = np.concatenate(parts) if parts else np.array([], dtype=np.float32)

        buffer = io.BytesIO()
        sf.write(buffer, audio_np, samplerate=24000, format="mp3")
        audio_bytes = buffer.getvalue()

        duration_ms = (time.monotonic() - started) * 1000

        return SynthesisResult(
            audio=audio_bytes,
            provider=self.name,
            voice=self._voice_name,
            characters=len(text),
            duration_ms=duration_ms,
            audio_duration_s=get_audio_duration(audio_bytes),
            file_size_bytes=len(audio_bytes),
            cost_usd=0.0,
        )
