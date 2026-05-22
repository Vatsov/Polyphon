# kokoro-audiobook

Convert a plain-text book into an MP3 audiobook using [Kokoro](https://github.com/hexgrad/kokoro) text-to-speech.

GPU-accelerated, fully resumable, with a small web UI for control.

## Features

- 🎙️ Natural speech via Kokoro-82M (`kokoro>=0.9.4`)
- ⚡ GPU synthesis (~8× realtime); also runs on CPU
- ⏯️ Resumable — interrupt any time, rerun to continue exactly where it stopped
- 🌐 Web control panel: pause / resume / stop
- 🔇 Configurable silence inserted between sentences
- 📦 ffmpeg collects all chunks into a single `audiobook.mp3`

## Requirements

- Python 3.10+
- `ffmpeg` and `espeak-ng` — `sudo apt install ffmpeg espeak-ng`
- Optional: an NVIDIA GPU

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# torch — pick one:
.venv/bin/pip install torch                              # CPU / modern GPU
# Maxwell GPUs (GTX 750 Ti / 9xx) need the CUDA 12.1 build:
.venv/bin/pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu121
```

## Usage

Put your text in `book.txt`, then run the whole pipeline:

```bash
./collector.sh
```

It converts the entire book and produces `audiobook.mp3`. While it runs, open
<http://127.0.0.1:8765/> to watch progress and pause / resume / stop.

### Converter only

```bash
.venv/bin/python book_to_speech.py            # convert (resumable)
.venv/bin/python book_to_speech.py --limit 8  # quick test: only 8 chunks
```

### Quick demo

```bash
.venv/bin/python joke_tts.py "Your one-liner here"
```

## How it works

1. `book.txt` is cleaned (front-matter and markup stripped) and split into
   1–2 sentence chunks.
2. Pending chunks live in `book-work.txt`, one per line — it shrinks from the
   top as work completes, so it doubles as the resume ledger.
3. Each chunk → Kokoro → an MP3 in `mp3/part_NNN/`, with trailing silence.
4. `collector.sh` ffmpeg-concatenates every chunk into `audiobook.mp3`.

Crash-safe: MP3s are written atomically and the worker skips any chunk that is
already done, so re-running never duplicates or loses audio.

## Notes

- Text cleaning in `build_clean_text()` (`book_to_speech.py`) is tuned for one
  ebook export — adjust the start marker and regexes for your own source.
- Bring your own text. Do not redistribute audio generated from copyrighted
  books.

## License

MIT — see [LICENSE](LICENSE).
