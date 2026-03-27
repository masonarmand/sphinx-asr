"""
Switchboard corpus adapter.
"""

import re
from pathlib import Path
from typing import Iterator

FILLERS = {"noise", "laughter", "vocalized-noise"}

# regex
LAUGHTER_WORD = re.compile(r"\[laughter-(\S+)\]", re.IGNORECASE)
BRACKET_TAG = re.compile(r"\[[^\]]+\]")
ANGLE_TAG = re.compile(r"<<[^>]+>>")
MULTI_SPACE = re.compile(r"\s+")

def clean_text(text: str) -> str:
    """
    clean switchboard transcript text

    expand [laughter-word] into [LAUGHTER] word
    keep [NOISE], [LAUGHTER], [VOCALIZED-NOISE] as filler tokens
    remove other tags (like [t], [d], [ou])
    remove <<word>> annotations
    uppercase everything
    collaspe whitespace
    """
    text = LAUGHTER_WORD.sub(r"[laughter] \1", text)

    # replace fillers with placeholders so they dont get messed up
    for filler in FILLERS:
        text = text.replace(f"[{filler}]", f"__{filler.upper()}__")

    text = BRACKET_TAG.sub("", text)
    text = ANGLE_TAG.sub("", text)

    # restore fillers
    for filler in FILLERS:
        text = text.replace(f"__{filler.upper()}__", f"[{filler.upper()}]")

    text = text.upper()
    text = MULTI_SPACE.sub(" ", text).strip()

    return text


def get_utterances(
        corpus_dir: Path,
        split_name: str,
        split_cfg: dict,
) -> Iterator[tuple[str, str]]:
    """
    yield (fileid, text) pairs for a librispeech split
    """
    trans_path = corpus_dir / split_cfg["transcripts"]
    if not trans_path.is_file():
        raise FileNoteFoundError(
            f"transcript file not found: {trans_path}\n"
            f"Have you downloaded the '{split_name}' split?"
        )

    sphinx_root = corpus_dir.parent.parent
    audio_dir = corpus_dir / "full" / "train" / "audio" / "utt"

    with open(trans_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # utt_id start_time end_time text
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue

            utt_id = parts[0]
            text = clean_text(parts[3])
            if not text:
                continue

            fileid = (audio_dir / utt_id).relative_to(sphinx_root)

            yield str(fileid), text
