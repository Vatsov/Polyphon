#!/usr/bin/env bash
# Convert the entire book.txt to one audiobook.mp3.
# Resumable: re-run any time - it continues from book-work.txt.
set -uo pipefail
cd "$(dirname "$0")"
PY="$PWD/.venv/bin/python"

echo "== Converting book.txt -> MP3 chunks =="
"$PY" book_to_speech.py
rc=$?

if [ -f book-work.txt ] && [ -s book-work.txt ]; then
    left=$(grep -c . book-work.txt)
    echo "Stopped early - $left chunks left. Re-run ./collector.sh to continue."
    exit "$rc"
fi

echo "== Collecting chunks -> audiobook.mp3 =="
: > concat_list.txt
find mp3 -name 'chunk_*.mp3' | sort | while read -r f; do
    printf "file '%s'\n" "$PWD/$f" >> concat_list.txt
done

if [ ! -s concat_list.txt ]; then
    echo "No chunk MP3s found." >&2
    exit 1
fi

ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 \
    -i concat_list.txt -c copy audiobook.mp3

dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 audiobook.mp3)
echo "Done -> audiobook.mp3  (${dur%.*}s of audio)"
