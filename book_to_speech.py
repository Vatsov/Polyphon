#!/usr/bin/env python3
"""book.txt -> MP3 chunks with Kokoro TTS (GPU). Resumable, batch=4, web control.

Run:   .venv/bin/python book_to_speech.py            # convert whole book
       .venv/bin/python book_to_speech.py --limit 8  # test: only 8 chunks
Web:   http://127.0.0.1:8765/   (pause / resume / stop at batch boundaries)

State files (all auto-created, safe to delete to restart from scratch):
  book-clean.txt  full cleaned prose (reference)
  book-work.txt   pending chunks, one per line - shrinks from the top as it runs
  state.json      total chunk count
  mp3/part_NNN/chunk_NNNNNN.mp3   output, 64 kbps mono, 0.5 s pause baked in
"""
import argparse, json, os, re, signal, subprocess, sys, threading, time, warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

# ---- config -----------------------------------------------------------------
VOICE          = "af_heart"
SR             = 24_000          # Kokoro output rate
PAUSE_SEC      = 0.5             # silence appended after each chunk
BATCH          = 4               # chunks per interruption-protected batch
CHUNKS_PER_DIR = 500
MP3_BITRATE    = "64k"
PORT           = 8765
MAX_SENTS      = 2               # sentences per chunk
MAX_CHARS      = 400             # char cap per chunk (keeps Kokoro from truncating)

BASE  = os.path.dirname(os.path.abspath(__file__))
SRC   = os.path.join(BASE, "book.txt")
CLEAN = os.path.join(BASE, "book-clean.txt")
WORK  = os.path.join(BASE, "book-work.txt")
STATE = os.path.join(BASE, "state.json")
MP3   = os.path.join(BASE, "mp3")


# ---- web control -------------------------------------------------------------
class Control:
    paused = False
    stop = False
    stats = {"total": 0, "done": 0, "rate_per_min": 0.0, "eta": "?"}

ctrl = Control()

PAGE = """<!doctype html><meta charset=utf-8><title>book TTS</title>
<meta http-equiv=refresh content=5>
<body style="font-family:sans-serif;max-width:460px;margin:40px auto">
<h2>Kokoro book converter</h2><pre>{s}</pre>
<form method=post action=/pause style=display:inline><button>Pause</button></form>
<form method=post action=/resume style=display:inline><button>Resume</button></form>
<form method=post action=/stop style=display:inline><button>Stop after batch</button></form>
</body>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence access log
        pass

    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self):
        info = {**ctrl.stats, "paused": ctrl.paused, "stopping": ctrl.stop}
        if self.path == "/status":
            self._json(200, info)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(PAGE.format(s=json.dumps(info, indent=2)).encode())

    def do_POST(self):
        if self.path == "/pause":
            ctrl.paused = True
        elif self.path == "/resume":
            ctrl.paused = False
        elif self.path == "/stop":
            ctrl.stop = True
        self._json(200, {"ok": True, "paused": ctrl.paused, "stopping": ctrl.stop})


def start_web(port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Web control: http://127.0.0.1:{port}/")


# ---- text prep ---------------------------------------------------------------
def build_clean_text(src):
    raw = open(src, encoding="utf-8", errors="ignore").read()
    i = raw.find("FORESHADOWING: THE STILL")      # skip cover / copyright / TOC
    body = raw[i:] if i != -1 else raw
    body = re.sub(r"-\n", "-", body)               # rejoin hyphenated line breaks
    body = body.replace("\n", " ")                 # un-wrap hard line breaks
    body = re.sub(r"\[\d+\]", "", body)            # drop [n] footnote markers
    body = body.replace("W e ", "We ")             # fix common extraction artifact
    return re.sub(r"\s+", " ", body).strip()


def make_chunks(text):
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    nlp.max_length = len(text) + 1000
    sents = [s.text.strip() for s in nlp(text).sents if s.text.strip()]
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        if cur and (len(cur) >= MAX_SENTS or cur_len + len(s) > MAX_CHARS):
            chunks.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += len(s) + 1
    if cur:
        chunks.append(" ".join(cur))
    return [c for c in chunks if c.strip()]


# ---- io helpers --------------------------------------------------------------
def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
    os.replace(tmp, path)


def chunk_path(idx):
    return os.path.join(MP3, f"part_{idx // CHUNKS_PER_DIR:03d}", f"chunk_{idx:06d}.mp3")


def encode_mp3(pcm_bytes, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
         "-b:a", MP3_BITRATE, "-f", "mp3", tmp],
        input=pcm_bytes, check=True)
    os.replace(tmp, path)


def fmt_dur(sec):
    sec = int(sec)
    return f"{sec // 3600}h{sec % 3600 // 60:02d}m"


# ---- synthesis ---------------------------------------------------------------
def synth_pcm(pipe, text, silence):
    parts = [np.asarray(a, dtype=np.float32) for _, _, a in pipe(text, voice=VOICE)]
    audio = np.concatenate(parts) if parts else np.zeros(SR // 2, np.float32)
    i16 = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    return np.concatenate([i16, silence]).tobytes()


def sigint(sig, frame):
    if ctrl.stop:
        print("\nForce exit.")
        os._exit(1)
    ctrl.stop = True
    print("\nSIGINT - stopping cleanly after current batch (Ctrl-C again to force).")


# ---- main --------------------------------------------------------------------
def run(args):
    warnings.filterwarnings("ignore")

    if not (os.path.exists(WORK) and os.path.exists(STATE)):
        print("First run: cleaning + chunking book.txt ...")
        text = build_clean_text(args.src)
        write_atomic(CLEAN, text)
        chunks = make_chunks(text)
        write_atomic(WORK, "\n".join(chunks) + "\n")
        json.dump({"total_chunks": len(chunks), "voice": VOICE,
                   "pause_sec": PAUSE_SEC}, open(STATE, "w"), indent=2)
        print(f"Prepared {len(chunks)} chunks.")

    total = json.load(open(STATE))["total_chunks"]
    pending = [l for l in open(WORK, encoding="utf-8").read().splitlines() if l.strip()]
    done0 = total - len(pending)
    print(f"{done0}/{total} done already, {len(pending)} chunks remaining.")
    if not pending:
        print("Nothing to do.")
        return 0

    ctrl.stats.update(total=total, done=done0)
    start_web(args.port)
    signal.signal(signal.SIGINT, sigint)

    print("Loading Kokoro on GPU ...")
    from kokoro import KPipeline
    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cuda")
    silence = np.zeros(int(PAUSE_SEC * SR), np.int16)

    t0, n = time.time(), 0
    while pending:
        for _ in range(BATCH):
            if not pending:
                break
            idx = total - len(pending)
            mp3 = chunk_path(idx)
            if not os.path.exists(mp3):           # idempotent: skip if already made
                encode_mp3(synth_pcm(pipe, pending[0], silence), mp3)
            pending.pop(0)                        # commit: drop converted line
            write_atomic(WORK, "\n".join(pending) + ("\n" if pending else ""))
            n += 1
            ctrl.stats["done"] = total - len(pending)
            if args.limit and n >= args.limit:
                break

        rate = n / max(time.time() - t0, 1e-6)
        eta = fmt_dur(len(pending) / rate) if rate else "?"
        ctrl.stats.update(rate_per_min=round(rate * 60, 1), eta=eta)
        print(f"[{total - len(pending)}/{total}] "
              f"{100 * (total - len(pending)) / total:5.1f}%  "
              f"{rate * 60:5.1f} chunks/min  ETA {eta}")

        if args.limit and n >= args.limit:
            print(f"--limit {args.limit} reached.")
            return 2
        if ctrl.stop:
            print("Stopped cleanly at batch boundary.")
            return 2
        while ctrl.paused and not ctrl.stop:
            time.sleep(0.5)
        if ctrl.stop:
            print("Stopped cleanly.")
            return 2

    print(f"Done - all {total} chunks converted.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=SRC, help="source text (default: book.txt)")
    ap.add_argument("--limit", type=int, default=0, help="stop after N chunks (testing)")
    ap.add_argument("--port", type=int, default=PORT, help="web control port")
    sys.exit(run(ap.parse_args()))
