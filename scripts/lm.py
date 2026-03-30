#!/usr/bin/env python3
"""
Build a trigram language model from training transcripts.

uses CMU SLM toolkit to build an LM (.arpa format)

Usage:
    lm.py <corpus> <split>
"""

import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from corpus import get_adapter
from lib.asr_util import err, get_sphinx_root
from lib.config import load_corpus


def find_tool(name: str, root: Path) -> Path:
    """find a cmu toolkit binary"""
    local = root / "bin" / platform.machine() / name
    if local.is_file():
        return local
    found = shutil.which(name)
    if found:
        return Path(found)
    err(f"{name} not found. Make sure to run 'make' to build the CMU toolkit.")


def extract_text(corpus: dict, split_name: str, root: Path) -> str:
    """extract cleaned text from training transcripts"""
    split_cfg = corpus["splits"][split_name]
    adapter = get_adapter(corpus["name"])
    lines = []
    utterances = adapter.get_utterances(
        corpus["_dir"],
        split_name,
        split_cfg,
        corpus
    )
    for _, text in utterances:
        lines.append(f"<s> {text} </s>")
    return "\n".join(lines) + "\n"


def build_lm(
        text: str,
        output_path: Path,
        root: Path,
        ngram_order: int = 3
) -> Path:
    """build ARPA language model from text using CMU SLM toolkit."""
    text2wfreq = find_tool("text2wfreq", root)
    wfreq2vocab = find_tool("wfreq2vocab", root)
    text2idngram = find_tool("text2idngram", root)
    idngram2lm = find_tool("idngram2lm", root)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        text_file = tmp / "train.txt"
        wfreq_file = tmp / "train.wfreq"
        vocab_file = tmp / "train.vocab"
        idngram_file = tmp / "train.idngram"

        text_file.write_text(text)
        print("  computing word frequencies...")
        _run(f"{text2wfreq} < {text_file} > {wfreq_file}")
        print("  building vocabulary...")
        _run(f"{wfreq2vocab} < {wfreq_file} > {vocab_file}")
        print(f"  counting {ngram_order}-grams...")
        _run(
            f"{text2idngram} -vocab {vocab_file} "
            f"-n {ngram_order} -temp {tmp}"
            f"< {text_file} > {idngram_file}"
        )
        print("  building arpa language model...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _run(
            f"{idngram2lm} -idngram {idngram_file} "
            f"-vocab {vocab_file} -arpa {output_path}"
        )

    return output_path


def _run(cmd: str):
    """run a shell command & exit on failure"""
    ret = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        check=False
    )
    if ret.returncode != 0:
        print(f"  Command failed: {cmd}")
        if ret.stderr:
            print(f"  {ret.stderr.strip()}")
        sys.exit(ret.returncode)


def main():
    """program entry"""
    parser = argparse.ArgumentParser(
        description="build a trigram language model from training transcripts"
    )
    parser.add_argument("corpus", help="Corpus name")
    parser.add_argument("split", help="Split name")
    parser.add_argument(
        "-n", "--order",
        type=int,
        default=3,
        help="N-gram order (default: 3)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output path (default: corpus/<name>/lm/<split>.arpa)",
    )
    args = parser.parse_args()
    root = get_sphinx_root()
    corpus = load_corpus(args.corpus, root)

    splits = corpus.get("splits", {})
    if args.split not in splits:
        available = ", ".join(splits.keys())
        err(f"Split '{args.split}' not found. Available: {available}")

    if args.output:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = root / output_path
    else:
        output_path = corpus["_dir"] / "lm" / f"{args.split}.arpa"

    print(f"building {args.order}-gram LM for {args.corpus}/{args.split}")
    print(f"  output: {output_path}")
    print(f"  extracting text from transcripts...")
    text = extract_text(corpus, args.split, root)
    line_count = text.count("\n")
    print(f"  {line_count} sentences")

    build_lm(text, output_path, root, args.order)

    print(f"\ndone. language model written to {output_path}")
    print(f"to use in an experiment, add to experiment.yml:")
    print(f"  decode:")
    print(f"    lm: {output_path.relative_to(root)}")


if __name__ == "__main__":
    main()
