"""Google Cloud Text-to-Speech provider."""

import time

from google.cloud import texttospeech  # type: ignore[import]

from polyphon.core.audio import get_audio_duration
from polyphon.providers.base import SynthesisResult, TTSProvider

# Pricing: https://cloud.google.com/text-to-speech/pricing
_COST_PER_MILLION: dict[str, float] = {
    "Standard": 4.0,
    "WaveNet": 16.0,
    "Neural2": 16.0,
    "Studio": 160.0,
    "Chirp3-HD": 30.0,
    "Chirp3": 30.0,
}


def _detect_tier(voice_name: str) -> float:
    for tier, cost in _COST_PER_MILLION.items():
        if tier.lower().replace("-", "") in voice_name.lower().replace("-", ""):
            return cost
    return _COST_PER_MILLION["Neural2"]  # safe default


class GoogleTTSProvider(TTSProvider):
    """
    Google Cloud TTS provider.

    Supported Bulgarian voices:
        - bg-BG-Standard-B        ($4/1M chars)
        - bg-BG-Chirp3-HD-Aoede   ($30/1M chars)
        - bg-BG-Chirp3-HD-Charon  ($30/1M chars)
        - ... (30 Chirp3-HD voices total)

    Auth: set GOOGLE_APPLICATION_CREDENTIALS env var to your key.json path.
    """

    def __init__(self, voice_name: str = "bg-BG-Chirp3-HD-Aoede", language_code: str = "bg-BG") -> None:
        self._voice_name = voice_name
        self._language_code = language_code
        self._client = texttospeech.TextToSpeechClient()
        self._cost_per_million = _detect_tier(voice_name)

    @property
    def name(self) -> str:
        return "google"

    @property
    def voice(self) -> str:
        return self._voice_name

    @property
    def cost_per_million_chars(self) -> float:
        return self._cost_per_million

    def synthesize(self, text: str) -> SynthesisResult:
        started = time.monotonic()

        response = self._client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code=self._language_code,
                name=self._voice_name,
            ),
            audio_config=texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
            ),
        )

        duration_ms = (time.monotonic() - started) * 1000
        audio = response.audio_content

        return SynthesisResult(
            audio=audio,
            provider=self.name,
            voice=self._voice_name,
            characters=len(text),
            duration_ms=duration_ms,
            audio_duration_s=get_audio_duration(audio),
            file_size_bytes=len(audio),
            cost_usd=self.estimate_cost(len(text)),
        )
