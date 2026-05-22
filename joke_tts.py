#!/usr/bin/env python3
"""Proof-of-concept: convert a short joke to speech with Kokoro (>=0.9.4).

Usage:
    python joke_tts.py                       # speaks the built-in joke
    python joke_tts.py "Your joke here"      # speaks a custom joke
    python joke_tts.py "..." --voice am_adam --out my.wav

First run downloads the ~330 MB Kokoro-82M model from Hugging Face.
"""
import argparse
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SAMPLE_RATE = 24_000  # Kokoro always outputs 24 kHz mono

DEFAULT_JOKE = (
    "Why don't scientists trust atoms? "
    "Because they make up everything!"
)


def joke_to_speech(text: str, voice: str = "af_heart", out_path: str = "joke.wav") -> str:
    """Synthesize `text` to a WAV file and return the output path."""
    # lang_code 'a' = American English; pin to CPU so it runs anywhere.
    pipeline = KPipeline(lang_code="a", device="cpu")

    chunks = []
    for graphemes, phonemes, audio in pipeline(text, voice=voice):
        print(f"  segment: {graphemes!r}")
        print(f"  phonemes: {phonemes}")
        chunks.append(np.asarray(audio, dtype=np.float32))

    if not chunks:
        raise RuntimeError("Kokoro produced no audio — is the input empty?")

    sf.write(out_path, np.concatenate(chunks), SAMPLE_RATE)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Speak a short joke with Kokoro TTS.")
    parser.add_argument("joke", nargs="?", default=DEFAULT_JOKE, help="joke text to speak")
    parser.add_argument("--voice", default="af_heart", help="Kokoro voice (e.g. af_heart, am_adam)")
    parser.add_argument("--out", default="joke.wav", help="output WAV path")
    args = parser.parse_args()

    print(f"Joke : {args.joke}")
    print(f"Voice: {args.voice}")
    out = joke_to_speech(args.joke, voice=args.voice, out_path=args.out)

    info = sf.info(out)
    print(f"Wrote {out} ({info.duration:.2f}s, {info.samplerate} Hz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
