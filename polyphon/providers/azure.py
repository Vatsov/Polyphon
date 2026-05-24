"""Microsoft Azure Cognitive Services TTS provider."""

import time

import azure.cognitiveservices.speech as speechsdk  # type: ignore[import]

from polyphon.core.audio import get_audio_duration
from polyphon.providers.base import SynthesisResult, TTSProvider

_COST_PER_MILLION = 16.0  # Neural Standard pricing

# Bulgarian neural voices available on Azure:
#   bg-BG-KalinaNeural  (female)
#   bg-BG-BorislavNeural (male)


class AzureTTSProvider(TTSProvider):
    """
    Azure Cognitive Services TTS provider.

    Auth: subscription_key + region (e.g. 'westeurope').
    """

    def __init__(
        self,
        subscription_key: str,
        region: str,
        voice_name: str = "bg-BG-KalinaNeural",
    ) -> None:
        self._voice_name = voice_name
        self._config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
        self._config.speech_synthesis_voice_name = voice_name
        self._config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
        )

    @property
    def name(self) -> str:
        return "azure"

    @property
    def voice(self) -> str:
        return self._voice_name

    @property
    def cost_per_million_chars(self) -> float:
        return _COST_PER_MILLION

    def synthesize(self, text: str) -> SynthesisResult:
        started = time.monotonic()

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self._config, audio_config=None)
        result = synthesizer.speak_text_async(text).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Azure TTS failed: {result.reason}")

        duration_ms = (time.monotonic() - started) * 1000
        audio = result.audio_data

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
