#!/usr/bin/env python3
"""
Prepares a corpus for training by:
- converting FLAC audio files to WAV

Usage:
    scripts/prep_corpus.py <corpus_dir>

Arguments:
    corpus_dir - path to corpus directory containing .flac files

Requirements:
    flac (apt install flac)
"""

import argparse
import subprocess
import sys
from pathlib import Path


def err(msg: str):
    """print error message to stderr and exit"""
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def is_flac_installed() -> bool:
    """returns true if flac is installed"""
    try:
        subprocess.run(["flac", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_flac_to_wav(root: str):
    """recursively converts flac files in directory to .wav"""
    flac_files = list(Path(root).rglob("*.flac"))

    if not flac_files:
        print("No FLAC files found.")
        return

    converted = 0
    skipped = 0
    failed = 0

    for flac in flac_files:
        if flac.with_suffix(".wav").exists():
            skipped += 1
            continue
        result = subprocess.run(
            ["flac", "-d", str(flac)],
            capture_output=True,
        )
        if result.returncode != 0:
            failed += 1
            print(f"  ERROR: {result.stderr.decode().strip()}")
        else:
            converted += 1
            print(f"  {flac} -> {flac.with_suffix(".wav")}")
    print(
        f"Done. Converted: {converted}, skipped: {skipped}, failed: {failed}."
    )


def main():
    """program entry point"""
    parser = argparse.ArgumentParser(
        description="Prep the corpus for training"
    )
    parser.add_argument(
        "corpus_dir",
        type=Path,
        help="path to the corpus",
    )
    args = parser.parse_args()

    if not is_flac_installed():
        err("'flac' is not installed. Install it with sudo apt install flac")

    if not args.corpus_dir.is_dir():
        err(f"corpus directory not found: {args.corpus_dir}")

    convert_flac_to_wav(args.corpus_dir)


if __name__ == "__main__":
    main()
