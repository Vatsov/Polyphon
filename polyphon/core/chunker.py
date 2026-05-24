"""Split plain text into sentence-level chunks for TTS synthesis."""

import re


_SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
_MAX_CHARS = 500  # Google Cloud TTS hard limit is 5000, but shorter = better prosody


def chunk_text(text: str, max_chars: int = _MAX_CHARS) -> list[str]:
    """
    Split text into synthesizable chunks.

    Each chunk is at most `max_chars` characters. Splits on sentence
    boundaries where possible, falling back to word boundaries.

    Args:
        text:      Input plain text.
        max_chars: Maximum characters per chunk.

    Returns:
        List of non-empty text chunks.
    """
    sentences = _SENTENCE_END.split(text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            # Sentence itself too long — split by words
            if len(sentence) > max_chars:
                chunks.extend(_split_by_words(sentence, max_chars))
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def _split_by_words(text: str, max_chars: int) -> list[str]:
    words = text.split()
    parts: list[str] = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                parts.append(current)
            current = word

    if current:
        parts.append(current)

    return parts
