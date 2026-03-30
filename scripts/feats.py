#!/usr/bin/env python3
"""
Pre-extract feature files (MFC) for a corpus split. Only needs to be done once
per split. Runs sphinx_fe on each audio file and writes the .mfc files
alongside the audio.

Usage:
    feats.py <corpus> <split>
    feats.py --list
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from lib.asr_util import err, get_sphinx_root
from lib.config import load_corpus

# formats sphinx_fe can directly read (without sox)
NATIVE_FORMATS = {"wav", "mswav", "nist", "raw", "sph"}


def find_sphinx_fe(root: Path) -> Path:
    """Find the sphinx_fe binary"""
    fe = root / "bin" / platform.machine() / "sphinx_fe"
    if fe.is_file():
        return fe
    found = shutil.which("sphinx_fe")
    if found:
        return Path(found)
    err("sphinx_fe not found.")


# TODO just pass corpus_config
def extract_one(
        sphinx_fe: str,
        audio_file: Path,
        mfc_file: Path,
        audio_ext: str,
        audio_type: str,
        sample_rate: int,
        num_filt: int = 25,
        lo_filt: int = 130,
        hi_filt: int = 6800,
) -> bool:
    """
    Extract features for a single audio file.
    returns true on success
    """
    args = [
        sphinx_fe,
        "-i", str(audio_file),
        "-o", str(mfc_file),
        "-samprate", str(sample_rate),
        "-nfilt", str(num_filt),
        "-lowerf", str(lo_filt),
        "-upperf", str(hi_filt),
        "-transform", "dct",
        "-lifter", "22",
    ]

    if audio_type == "nist" or audio_ext == "sph":
        args.extend(["-nist", "yes"])
    elif audio_type == "raw" or audio_ext == "raw":
        args.extend(["-raw", "yes", "-input_endian", "little"])
    elif audio_type == "mswav" or audio_ext in ("wav", "mswav"):
        args.extend(["-mswav", "yes"])
    elif audio_ext not in NATIVE_FORMATS:
        args.extend(["-sox", "yes"])
    else:
        args.extend(["-input_endian", "little"])

    ret = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )

    if ret.returncode != 0:
        print(f"FAIL: {audio_file}")
        if ret.stderr:
            print(ret.stderr)

    return ret.returncode == 0


def extract_features(
        sphinx_fe: Path,
        audio_dir: Path,
        audio_ext: str,
        audio_type: str,
        sample_rate: int,
        num_filt: int = 25,
        lo_filt: int = 130,
        hi_filt: int = 6800,
        jobs: int = 1
) -> tuple[int, int, int]:
    """
    extract MFC features for all audio files in a directory.
    skips files that already have a .mfc file.
    returns: (extracted, skipped, failed) counts.
    """
    audio_files = sorted(audio_dir.rglob(f"*.{audio_ext}"))
    total = len(audio_files)

    if total == 0:
        print(f"  no .{audio_ext} files found in {audio_dir}")
        return (0, 0, 0)

    to_extract = []
    skipped = 0
    for audio_file in audio_files:
        mfc_file = audio_file.with_suffix(".mfc")

        # if size is only 4 bytes that means its a corrputed/invalid
        # mfc file, so we'd need to regenerate
        if mfc_file.is_file() and mfc_file.stat().st_size > 4:
            skipped += 1
        else:
            to_extract.append((audio_file, mfc_file))

    if not to_extract:
        print(f"  All {skipped} files already cached.")
        return (0, skipped, 0)

    print(f"  {len(to_extract)} to extract, {skipped} already cached")

    extracted = 0
    failed = 0
    fe_str = str(sphinx_fe)

    def _do_one(pair):
        audio_file, mfc_file = pair
        mfc_file.parent.mkdir(parents=True, exist_ok=True)
        return extract_one(
            fe_str,
            audio_file,
            mfc_file,
            audio_ext,
            audio_type,
            sample_rate,
            num_filt,
            lo_filt,
            hi_filt
        )

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(_do_one, pair): pair for pair in to_extract}
        for future in as_completed(futures):
            if future.result():
                extracted += 1
            else:
                failed += 1
            done = extracted + failed
            if done % 500 == 0 or done == len(to_extract):
                print(
                    f"  {done}/{len(to_extract)} ({extracted} ok, "
                    f"{failed} failed)"
                )
        return (extracted, skipped, failed)


# TODO maybe move this to lib/
# also theres a similar function in new_experiment.py
# could be combined into one with a flag denoting whether or not to list splits
def list_corpora(root: Path):
    """List available corpora and their splits"""
    corpus_dir = root / "corpus"
    if not corpus_dir.is_dir():
        print("No corpora found.")
        return

    for corpus_path in sorted(corpus_dir.iterdir()):
        yml = corpus_path / "corpus.yml"
        if not yml.is_file():
            continue
        corpus = load_corpus(corpus_path.name, root)
        print(f"\n{corpus_path.name}:")
        for split_name, split_cfg in corpus.get("splits", {}).items():
            audio_dir = corpus_path / split_cfg.get("audio", split_name)
            status = "[available]" if audio_dir.is_dir() else "[not downloaded]"
            print(f"  {split_name:<25} {status}")


def process_split(
        split: str,
        corpus_config: dict,
        root: Path,
        jobs: int
) -> tuple[int, int, int]:
    """
    genfeats for a split
    returns: extracted, skipped, failed
    """
    splits = corpus_config.get("splits", {})
    if split not in splits:
        available = ", ".join(splits.keys())
        err(f"split '{split}' not found. Available: {available}")

    split_cfg = splits[split]
    corpus_dir = corpus_config["_dir"]
    audio_rel = split_cfg.get("audio") or corpus_config.get("audio_dir")
    if not audio_rel:
        err(f"no audio directory defined for split '{split}' or corpus")
    audio_dir = corpus_dir / audio_rel
    audio_ext = corpus_config.get("audio_format", "wav")
    audio_type = corpus_config.get("audio_type", "")
    sample_rate = int(corpus_config.get("sample_rate", 16000))
    num_filt = int(corpus_config.get("num_filt", 25))
    lo_filt = int(corpus_config.get("lo_filt", 130))
    hi_filt = int(corpus_config.get("hi_filt", 6800))

    if not audio_dir.is_dir():
        err(f"audio directory not found: {audio_dir}")

    sphinx_fe = find_sphinx_fe(root)

    print(f"Extracting features for {corpus_config["name"]}/{split}")
    print(f"  Audio: {audio_dir}")
    print(f"  Format: {audio_ext} @ {sample_rate}Hz")
    print(f"  Jobs: {jobs}")

    return extract_features(
        sphinx_fe,
        audio_dir,
        audio_ext,
        audio_type,
        sample_rate,
        num_filt,
        lo_filt,
        hi_filt,
        jobs
    )


def main():
    """program entry"""
    parser = argparse.ArgumentParser(
        description="Pre-extract MFC features for a corpus split"
    )
    parser.add_argument(
        "corpus",
        nargs="?",
        help="corpus name"
    )
    parser.add_argument(
        "split",
        nargs="?",
        help="split name or 'all' for all splits"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available corpora and splits"
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=os.cpu_count() or 4,
        help=f"Parallel jobs (default: {os.cpu_count() or 4})",
    )
    args = parser.parse_args()
    root = get_sphinx_root()

    if args.list:
        list_corpora(root)
        sys.exit(0)

    if not args.corpus or not args.split:
        parser.print_help()
        sys.exit(1)

    # load corpus config
    corpus = load_corpus(args.corpus, root)
    extracted = 0
    skipped = 0
    failed = 0
    if args.split == "all":
        split_list = list(corpus["splits"])
        print("Generating features for the following splits:")
        for split in split_list:
            print(f"  {args.corpus}/{split}")
        for split in split_list:
            results = process_split(split, corpus, root, args.jobs)
            extracted += results[0]
            skipped += results[1]
            failed += results[2]
            print(f"Processed split: {split}\n")
            print(
                f"  {results[0]} extracted, {results[1]} cached, "
                f"{results[2]} failed"
            )
    else:
        extracted, skipped, failed = process_split(args.split, corpus, root, args.jobs)

    print(f"\nDone. {extracted} extracted, {skipped} cached, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
