"""Audio utilities — silence padding, MP3 concatenation, duration probing."""

import json
import subprocess
from pathlib import Path


_SILENCE_MS_DEFAULT = 500


def add_silence(audio: bytes, silence_ms: int = _SILENCE_MS_DEFAULT) -> bytes:
    """
    Append silence to an MP3 byte string using ffmpeg.

    Args:
        audio:      Raw MP3 bytes.
        silence_ms: Milliseconds of silence to append.

    Returns:
        MP3 bytes with silence appended.
    """
    silence_sec = silence_ms / 1000
    result = subprocess.run(  # noqa: S603
        [
            "ffmpeg", "-y",
            "-i", "pipe:0",
            "-af", f"apad=pad_dur={silence_sec}",
            "-f", "mp3",
            "pipe:1",
        ],
        input=audio,
        capture_output=True,
        check=True,
    )
    return result.stdout


def get_audio_duration(audio: bytes) -> float:
    """
    Return the duration of an MP3 byte string in seconds using ffprobe.

    Args:
        audio: Raw MP3 bytes.

    Returns:
        Duration in seconds, or 0.0 if ffprobe fails.
    """
    try:
        result = subprocess.run(  # noqa: S603
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-i", "pipe:0",
            ],
            input=audio,
            capture_output=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:  # noqa: BLE001
        # Fallback: estimate from 128kbps bitrate
        return len(audio) / (128 * 1024 / 8)


def concat_mp3s(chunk_files: list[Path], output_path: Path) -> None:
    """
    Concatenate a list of MP3 files into a single output file using ffmpeg.

    Args:
        chunk_files: Ordered list of MP3 chunk paths.
        output_path: Destination MP3 file.
    """
    list_file = output_path.parent / "_concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in chunk_files))

    subprocess.run(  # noqa: S603
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    list_file.unlink()
