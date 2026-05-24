"""Basic usage example — convert a text file to MP3 using Google Cloud TTS."""

from pathlib import Path

from polyphon import GoogleTTSProvider, Pipeline

# Set GOOGLE_APPLICATION_CREDENTIALS in .env before running.

pipeline = Pipeline(
    provider=GoogleTTSProvider(voice_name="bg-BG-Chirp3-HD-Aoede"),
    output_dir=Path("output"),
)

text = Path("book.txt").read_text(encoding="utf-8")
output = pipeline.run(text=text, output_name="my_book")

print(f"Audiobook saved to: {output}")
