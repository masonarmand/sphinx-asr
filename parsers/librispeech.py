#!/usr/bin/env python3
"""
Parses a librispeech corpus split into sphinxtrain compatible fileids and
transcription files.

Usage:
    parsers/librispeech.py <split_dir> <fileids_out> <transcription_out>
"""

import argparse
import sys
from pathlib import Path


def err(msg: str):
    """print error message to stderr and exit"""
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)

def parse_transcripts(
        split_dir: Path,
        fileids_out: Path,
        transcription_out: Path
):
    """Parse all .trans.txt files in a librispeech split directory

    each .trans.txt line has the format:
        <utt_id> <UPPERCASE TEXT>

    writes fileids in the format:
        <speakder>/<chapter>/<utt_id>

    writes transcriptions in the format:
        <s> TEXT </s> (<utt_id>)

    Args:
        split_dir: path to a librispeech split (e.g dev-clean)
        fileids_out: path to write the fileids list
        transcription_out: path to write the transcription file
    """
    trans_files = sorted(split_dir.rglob("*.trans.txt"))
    if not trans_files:
        err(f"no .trans.txt files found in {split_dir}")

    with fileids_out.open("w") as fids, transcription_out.open("w") as trans:
        for trans_file in trans_files:
            rel_dir = trans_file.parent.relative_to(split_dir)

            for line in trans_file.read_text().splitlines():
                if not line.strip():
                    continue
                utt_id, _, text = line.partition(" ")
                fids.write(f"{rel_dir}/{utt_id}\n")
                trans.write(f"<s> {text} </s> ({utt_id})\n")

    count = sum(1 for _ in fileids_out.open())
    print(f"Parsed {count} utterances.")


def main():
    """program entry point"""
    parser = argparse.ArgumentParser(
        description="Parse librispeech corpus into sphinxtrain format"
    )
    parser.add_argument(
        "split_dir",
        type=Path,
        help="path to librispeech split (e.g. corpus/LibriSpeech/dev-clean)",
    )
    parser.add_argument(
        "fileids_out",
        type=Path,
        help="path to write fileids list",
    )
    parser.add_argument(
        "transcription_out",
        type=Path,
        help="path to write transcription file",
    )
    args = parser.parse_args()

    if not args.split_dir.is_dir():
        err(f"Split directory not found: {args.split_dir}")

    args.fileids_out.parent.mkdir(parents=True, exist_ok=True)
    args.transcription_out.parent.mkdir(parents=True, exist_ok=True)
    parse_transcripts(args.split_dir, args.fileids_out, args.transcription_out)


if __name__ == "__main__":
    main()
