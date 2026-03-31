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
import threading
import re
from pathlib import Path

from lib.asr_util import get_sphinx_root, err, waitbar, spinner

def get_npart(exp_dir: Path) -> int:
    """read DEC_CFG_NPART from the generated sphinx_train.cfg"""
    cfg_path = exp_dir / "etc" / "sphinx_train.cfg"
    if not cfg_path.is_file():
        return 1
    for line in cfg_path.read_text().splitlines():
        m = re.match(r'^\s*\$DEC_CFG_NPART\s*=\s*(\d+)', line)
        if m:
            return int(m.group(1))
    return 1


def get_total_utterances(exp_dir: Path, db_name: str) -> int:
    """count utterances in the decode fileids file"""
    fileids = exp_dir / "etc" / f"{db_name}_decode.fileids"
    if not fileids.is_file():
        return 0
    return sum(1 for _ in fileids.open())


def poll_progress(
        result_dir: Path,
        db_name: str,
        npart: int,
        total: int,
        stop_event: threading.Event
):
    """poll match files to show decode progress"""
    spin_idx = 0
    in_align = False
    while not stop_event.is_set():
        combined = result_dir / f"{db_name}.match"

        if combined.is_file():
            # alignment
            if not in_align:
                print(
                    waitbar(total, total, label="decoding"),
                    end="",
                    flush=True
                )
                print("Decode phase complete. Moving to aligning phase.")
                in_align = True
            print(spinner(spin_idx, "aligning..."), end="", flush=True)
            spin_idx += 1
            stop_event.wait(timeout=0.25)
        else:
            # decode
            completed = 0
            for i in range(1, npart + 1):
                match = result_dir / f"{db_name}-{i}-{npart}.match"
                if match.is_file():
                    try:
                        completed += sum(1 for _ in match.open())
                    except OSError:
                        pass
            print(waitbar(completed, total, label="decoding"), end="", flush=True)
            stop_event.wait(timeout=5)
    print()


# TODO clean this up by splitting into multiple functions
def main():
    """program entry"""
    parser = argparse.ArgumentParser(description="Run sphinxtrain decoding.")
    parser.add_argument("exp_dir", type=Path)
    args = parser.parse_args()

    root = get_sphinx_root()
    exp_dir = args.exp_dir
    if not exp_dir.is_absolute():
        exp_dir = root / exp_dir

    db_name = exp_dir.name

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

    npart = get_npart(exp_dir)
    total_utts = get_total_utterances(exp_dir, db_name)
    result_dir = exp_dir / "result"

    # cleanup old files
    for f in result_dir.glob("*.match"):
        f.unlink()
    for f in result_dir.glob("*.matchseg"):
        f.unlink()

    os.chdir(exp_dir)
    print(f"Decoding experiment {exp_dir.name}...")

    stop_event = threading.Event()
    progress_thread = threading.Thread(
        target=poll_progress,
        args=(result_dir, db_name, npart, total_utts, stop_event),
        daemon=True,
    )
    progress_thread.start()

    start = time.monotonic()
    ret = subprocess.call(
        ["perl", str(decode_script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    output_lines = []
    with subprocess.Popen(
        ["perl", str(decode_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ) as proc:
        for line in proc.stdout:
            output_lines.append(line)
    ret = proc.returncode
    output = "".join(output_lines)

    elapsed = time.monotonic() - start
    minutes, seconds = divmod(int(elapsed), 60)

    stop_event.set()
    progress_thread.join()

    if ret != 0:
        print(f"\nError: decoding failed (exit {ret})")
        log_dir = exp_dir / "logdir" / "decode"
        if log_dir.is_dir():
            for log in sorted(log_dir.glob("*.log"))[:1]:
                lines = log.read_text(errors="replace").splitlines()
                print(f"\n--- {log.name} (last 20 lines) ---")
                print("\n".join(lines[-20:]))
        sys.exit(ret)

    print(f"\nDecoding complete. Time: {minutes}m {seconds}s")

    # print WER
    for line in output_lines:
        if "WORD ERROR" in line or "SENTENCE ERROR" in line:
            print(line.strip())

    if result_dir.is_dir() and any(result_dir.iterdir()):
        print(f"Results written to {result_dir}")


if __name__ == "__main__":
    main()
