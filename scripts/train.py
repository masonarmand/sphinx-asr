#!/usr/bin/env python3
"""
Run sphinxtrain training pipeline.

Usage:
    train.py <experiment_dir>
"""

import time
import argparse
import os
import subprocess
import sys
from pathlib import Path
from lib.asr_util import get_sphinx_root

STEPS = [
    # "000.comp_feat/slave_feat.pl",
    "00.verify/verify_all.pl",
    #"0000.g2p_train/g2p_train.pl",
    "01.lda_train/slave_lda.pl",
    "02.mllt_train/slave_mllt.pl",
    "05.vector_quantize/slave.VQ.pl",
    "10.falign_ci_hmm/slave_convg.pl",
    "11.force_align/slave_align.pl",
    "12.vtln_align/slave_align.pl",
    "20.ci_hmm/slave_convg.pl",
    "30.cd_hmm_untied/slave_convg.pl",
    "40.buildtrees/slave.treebuilder.pl",
    "45.prunetree/slave.state-tying.pl",
    "50.cd_hmm_tied/slave_convg.pl",
    "90.deleted_interpolation/deleted_interpolation.pl",
]

# TODO
def main():
    """program entry"""
    parser = argparse.ArgumentParser(description="Run sphinxtrain training.")
    parser.add_argument("exp_dir", type=Path)
    args = parser.parse_args()

    root = get_sphinx_root()
    exp_dir = args.exp_dir
    if not exp_dir.is_absolute():
        exp_dir = root / exp_dir

    scripts_dir = root / "vendor" / "sphinxtrain" / "scripts"
    os.chdir(exp_dir)

    start = time.monotonic()
    for step in STEPS:
        print(f"\n=== {step} ===")
        step_start = time.monotonic()
        ret = subprocess.call(["perl", str(scripts_dir / step)])
        step_elapsed = time.monotonic() - step_start
        minutes, seconds = divmod(int(step_elapsed), 60)
        print(f"=== Step time: {minutes}m {seconds}s ===")
        if ret != 0:
            print(f"Error: {step} failed (exit {ret})")
            sys.exit(ret)

    elapsed = time.monotonic() - start
    hours, remainder = divmod(int(elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"\nTraining complete. Total time: {hours}h {minutes}m {seconds}s")


if __name__ == "__main__":
    main()
