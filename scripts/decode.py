#!/usr/bin/env python3
"""
Run sphinxtrain decoding pipeline.

Usage:
    decode.py <experiment_dir>
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from lib.asr_util import get_sphinx_root, err

def main():
    """program entry"""
    parser = argparse.ArgumentParser(description="Run sphinxtrain decoding.")
    parser.add_argument("exp_dir", type=Path)
    args = parser.parse_args()

    root = get_sphinx_root()
    exp_dir = args.exp_dir
    if not exp_dir.is_absolute():
        exp_dir = root / exp_dir

    cfg_file = exp_dir / "etc" / "sphinx_train.cfg"
    if not cfg_file.is_file():
        err(f"{cfg_file} not found. Run 'sphinx setup {args.exp_dir}' first")

    # check for trained model
    model_dir = exp_dir / "model_parameters"
    if not model_dir.is_dir() or not any(model_dir.iterdir()):
        err(
            f"no trained models found in {model_dir}. "
            f"Run 'sphinx train {args.exp_dir}' first"
        )

    decode_script = (
        root / "vendor" / "sphinxtrain" / "scripts" / "decode" / "slave.pl"
    )
    if not decode_script.is_file():
        err("decode script not found at {decode_script}")

    os.chdir(exp_dir)
    print(f"Decoding experiment {exp_dir.name}...")
    start = time.monotonic()
    ret = subprocess.call(["perl", str(decode_script)])
    elapsed = time.monotonic() - start
    minutes, seconds = divmod(int(elapsed), 60)

    if ret != 0:
        print(f"\nError: decoding failed (exit {ret})")
        sys.exit(ret)

    print(f"\nDecoding complete. Time: {minutes}m {seconds}s")

    # check for results
    result_dir = exp_dir / "result"
    if result_dir.is_dir() and any(result_dir.iterdir()):
        print(f"Results written to {result_dir}")
        for f in sorted(result_dir.iterdir()):
            print(f"  {f.name}")


if __name__ == "__main__":
    main()
