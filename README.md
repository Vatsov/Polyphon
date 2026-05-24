<p align="center">
  <img src="assets/hero.png" alt="Polyphon" width="100%" />
</p>

<h1 align="center">Polyphon</h1>

<p align="center">
  <strong>Pluggable text-to-speech pipeline for audiobook generation.</strong><br/>
  Swap TTS providers without changing your workflow. Compare cost, latency, and voice quality — all in one place.
</p>

<p align="center">
  <a href="#install"><img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square" alt="Python 3.11+" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/code%20style-ruff-purple?style=flat-square" alt="Ruff" />
  <img src="https://img.shields.io/badge/types-mypy%20strict-blue?style=flat-square" alt="mypy strict" />
</p>

---

## Why Polyphon?

TTS providers differ — in price, voice quality, supported languages, and latency. Polyphon gives you a single pipeline that works with any of them, so you can:

- **Switch providers** without rewriting your conversion logic
- **Compare quality and cost** side-by-side on the same text
- **Track every synthesis call** — characters, latency, cost — through a built-in dashboard
- **Resume interrupted jobs** — crash-safe by design, picks up exactly where it stopped

---

## Supported Providers

| Provider | Languages | Best for | Docs |
|----------|-----------|----------|------|
| **Google Cloud TTS** | 50+ (incl. Bulgarian Chirp3-HD) | Best price/quality ratio | [→](polyphon/providers/google.py) |
| **ElevenLabs** | 28+ (Multilingual v2) | Highest voice naturalness, voice cloning | [→](polyphon/providers/elevenlabs.py) |
| **Azure Cognitive Services** | 140+ | Enterprise, reliable SLA | [→](polyphon/providers/azure.py) |
| **Kokoro-82M** | 9 (local, offline) | Privacy, no API cost | [→](polyphon/providers/kokoro.py) |

Adding a new provider takes ~30 lines — implement the `TTSProvider` interface and you're done.

---

## Quick Start

### 1. Install system dependencies (once)

**macOS:**
```bash
brew install uv ffmpeg
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
apt install ffmpeg
```

### 2. Install Python dependencies (once)

```bash
uv sync --extra google
```

### 3. Configure credentials

```bash
cp .env.example .env
# → fill in your API key in .env
```

### 4. Run

```bash
uv run polyphon convert book.txt
```

That's it. `uv` handles the virtual environment and Python version automatically.

---

## All commands

```bash
uv run polyphon book.txt                               # convert with Google (default)
uv run polyphon book.txt --provider elevenlabs         # use ElevenLabs
uv run polyphon book.txt --voice bg-BG-Chirp3-HD-Kore  # different voice
uv run polyphon book.txt --limit 5                     # test with 5 sentences only
uv run polyphon book.txt --dashboard                   # open dashboard after conversion
uv run polyphon dashboard                              # start dashboard standalone
uv run polyphon providers                              # list providers + credential status
```

---

## Use as a library

```python
from polyphon import GoogleTTSProvider, Pipeline

pipeline = Pipeline(
    provider=GoogleTTSProvider(voice_name="bg-BG-Chirp3-HD-Aoede"),
    output_dir=Path("output"),
)

pipeline.run(text=Path("book.txt").read_text(), output_name="my_book")
```

All providers follow the same interface — swap `GoogleTTSProvider` for `ElevenLabsProvider` or `AzureTTSProvider` without changing anything else.

---

## Dashboard

Start the metrics dashboard while a job is running:

```bash
uv run polyphon dashboard
# → http://127.0.0.1:8765
```

The dashboard shows live charts for latency, characters processed, and requests per provider. It auto-refreshes every 10 seconds.

---

## Add a Provider

Implement two properties and one method:

```python
from polyphon.providers.base import TTSProvider, SynthesisResult

class MyProvider(TTSProvider):
    @property
    def name(self) -> str:
        return "my-provider"

    @property
    def voice(self) -> str:
        return "my-voice-id"

    def synthesize(self, text: str) -> SynthesisResult:
        audio = my_api.tts(text)          # bytes
        return SynthesisResult(
            audio=audio,
            provider=self.name,
            voice=self.voice,
            characters=len(text),
            duration_ms=...,
        )
```

---

## Project Structure

```
polyphon/
├── core/
│   ├── pipeline.py     # orchestrator — ties everything together
│   ├── chunker.py      # splits text into sentence-level chunks
│   ├── state.py        # resumable progress (JSON ledger)
│   └── audio.py        # silence padding + MP3 concat (ffmpeg)
├── providers/
│   ├── base.py         # TTSProvider abstract interface
│   ├── google.py
│   ├── elevenlabs.py
│   ├── azure.py
│   └── kokoro.py
├── metrics/
│   ├── collector.py    # in-memory accumulator → JSON report
│   └── db.py           # SQLite sink for dashboard queries
└── dashboard/
    ├── server.py        # lightweight HTTP server
    └── static/          # Chart.js dashboard (dark theme)
```

---

## Development

```bash
make dev      # install dev tools + pre-commit hooks
make test     # run tests
make lint     # ruff
make typecheck # mypy
```

Code style is enforced by **Ruff** (formatting + linting) and **mypy strict** (type checking). Both run as pre-commit hooks — no manual formatting needed.

---

## Requirements

- Python 3.11+
- `ffmpeg` — `brew install ffmpeg` / `apt install ffmpeg`
- Provider credentials (API key or service account)

---

## License

MIT — see [LICENSE](LICENSE).

> Bring your own text. Do not redistribute audio generated from copyrighted works.
