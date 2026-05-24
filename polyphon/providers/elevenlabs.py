"""ElevenLabs TTS provider."""

import time

import httpx

from polyphon.core.audio import get_audio_duration
from polyphon.providers.base import SynthesisResult, TTSProvider

_API_BASE = "https://api.elevenlabs.io/v1"
_COST_PER_MILLION = 300.0  # Creator tier overage (~$0.30/1K chars)


class ElevenLabsProvider(TTSProvider):
    """
    ElevenLabs TTS provider (Multilingual v2).

    Bulgarian is supported via the multilingual_v2 model.

    Auth: set api_key or ELEVENLABS_API_KEY env var.
    """

    def __init__(self, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> None:
        self._api_key = api_key
        self._voice_id = voice_id

    @property
    def name(self) -> str:
        return "elevenlabs"

    @property
    def voice(self) -> str:
        return self._voice_id

    @property
    def cost_per_million_chars(self) -> float:
        return _COST_PER_MILLION

    def synthesize(self, text: str) -> SynthesisResult:
        started = time.monotonic()

        response = httpx.post(
            f"{_API_BASE}/text-to-speech/{self._voice_id}",
            headers={"xi-api-key": self._api_key},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "output_format": "mp3_44100_128",
            },
            timeout=30,
        )
        response.raise_for_status()

        duration_ms = (time.monotonic() - started) * 1000
        audio = response.content

        return SynthesisResult(
            audio=audio,
            provider=self.name,
            voice=self._voice_id,
            characters=len(text),
            duration_ms=duration_ms,
            audio_duration_s=get_audio_duration(audio),
            file_size_bytes=len(audio),
            cost_usd=self.estimate_cost(len(text)),
        )
