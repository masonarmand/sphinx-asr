#!/usr/bin/env python3
"""
librispeech corpus adapter
"""

from pathlib import Path
from typing import Iterator


def get_utterances(
        corpus_dir: Path,
        split_name: str,
        split_cfg: dict,
) -> Iterator[tuple[str, str]]:
    """
    yield (fileid, text) pairs for a librispeech split
    """
    audio_dir = corpus_dir / split_cfg.get("audio", split_name)

    if not audio_dir.is_dir():
        raise FileNotFoundError(
            f"Audio directory not found: {audio_dir}\n"
            f"Have you downloaded the '{split_name}' split?"
        )

    for trans_file in sorted(audio_dir.rglob("*.trans.txt")):
        utt_dir = trans_file.parent
        sphinx_root = corpus_dir.parent.parent

        with open(trans_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                utt_id, text = line.split(" ", 1)
                fileid = (utt_dir / utt_id).relative_to(sphinx_root)

                yield str(fileid), text
