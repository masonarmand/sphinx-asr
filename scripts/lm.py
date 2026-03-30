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


def extract_text_from_split(corpus: dict, split_name: str, root: Path) -> str:
    """extract cleaned text from a split's transcripts"""
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


def extract_text_from_full(corpus: dict, root: Path) -> str:
    """extract cleaned text from the full corpus transcript"""
    full_trans_rel = corpus.get("full_transcripts")
    if not full_trans_rel:
        err(
            f"corpus '{corpus['name']}' has no 'full_transcripts' defined in "
            "corpus.yml. Add a 'full_transcripts' key pointing to the full "
            "transcript file, or use a specific split instead:"
            f"\n  lm.py {corpus['name']} <split>"
        )
    trans_path = corpus["_dir"] / full_trans_rel
    if not trans_path.is_file():
        err(f"full transcript not found: {trans_path}")

    # create throwaway split config for get_utterances that points to the full
    # transcript
    full_split_cfg = {"transcripts": full_trans_rel}
    adapter = get_adapter(corpus["name"])
    lines = []
    utterances = adapter.get_utterances(
        corpus["_dir"],
        "full",
        full_split_cfg,
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
    parser.add_argument(
        "split",
        nargs="?",
        help="Split name"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "build LM from full corpus transcript "
            "(corpus.yml full_transcripts)"
        ),
    )
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

    if args.all and args.split:
        err("cannot use both a split name and --all")
    if not args.all and not args.split:
        parser.print_help()
        sys.exit(1)

    if args.output:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = root / output_path
    elif args.all:
        output_path = corpus["_dir"] / "lm" / f"{args.corpus}.arpa"
    else:
        output_path = corpus["_dir"] / "lm" / f"{args.split}.arpa"

    if args.all:
        print(f"building {args.order}-gram LM for {args.corpus} (full corpus)")
        text = extract_text_from_full(corpus, root)
    else:
        splits = corpus.get("splits", {})
        if args.split not in splits:
            available = ", ".join(splits.keys())
            err(f"Split '{args.split}' not found. Available: {available}")
        print(f"building {args.order}-gram LM for {args.corpus}/{args.split}")
        text = extract_text(corpus, args.split, root)

    line_count = text.count("\n")

    print(f"  output: {output_path}")
    print(f"  extracting text from transcripts...")
    print(f"  {line_count} sentences")

    build_lm(text, output_path, root, args.order)

    print(f"\ndone. language model written to {output_path}")
    if not corpus.get("lm"):
        print(f"to use as the default LM for this corpus, add to corpus.yml:")
        print(f"  lm: {output_path.relative_to(corpus['_dir'])}")
    print(f"to override in an experiment, add to experiment.yml:")
    print(f"  decode:")
    print(f"    lm: {output_path.relative_to(root)}")


if __name__ == "__main__":
    main()
