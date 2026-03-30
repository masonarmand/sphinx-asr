#!/usr/bin/env python3
"""
Run sphinxtrain training pipeline.

Usage:
    train.py <experiment_dir>
"""

import argparse
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from lib.asr_util import get_sphinx_root
from lib.config import load_experiment

@dataclass
class TrainingStep:
    """
    represents a single sphinxtrain training step
    """
    script: str
    # artifact files that must exist and not be empty after this step
    artifacts: list[str] = field(default_factory=list)
    # log directory to scan for errors for this step
    log_dir: str = ""
    # fatal log patterns
    fatal_patterns: list[str] = field(
        default_factory=lambda: ["0 frames", "FATAL"]
    )
    # warning log patterns
    warning_patterns: list[str] = field(
        default_factory=lambda: ["failed", "Aborting"]
    )

    @property
    def name(self) -> str:
        """short display name"""
        return self.script.rsplit("/", 1)[0]


STEPS = [
    TrainingStep(
        script="00.verify/verify_all.pl",
    ),
    TrainingStep(
        script="01.lda_train/slave_lda.pl",
        artifacts=["{db}.lda"],
        log_dir="01.lda_train",
    ),
    TrainingStep(
        script="02.mllt_train/slave_mllt.pl",
        artifacts=["{db}.mllt"],
        log_dir="02.mllt_train",
    ),
    TrainingStep(
        script="05.vector_quantize/slave.VQ.pl",
    ),
    TrainingStep(
        script="10.falign_ci_hmm/slave_convg.pl",
        log_dir="10.falign_ci_hmm",
    ),
    TrainingStep(
        script="11.force_align/slave_align.pl",
        log_dir="11.force_align",
    ),
    TrainingStep(
        script="12.vtln_align/slave_align.pl",
        log_dir="12.vtln_align",
    ),
    TrainingStep(
        script="20.ci_hmm/slave_convg.pl",
        log_dir="20.ci_hmm",
    ),
    TrainingStep(
        script="30.cd_hmm_untied/slave_convg.pl",
        log_dir="30.cd_hmm_untied",
    ),
    TrainingStep(
        script="40.buildtrees/slave.treebuilder.pl",
        log_dir="40.buildtrees",
    ),
    TrainingStep(
        script="45.prunetree/slave.state-tying.pl",
        log_dir="45.prunetree",
    ),
    TrainingStep(
        script="50.cd_hmm_tied/slave_convg.pl",
        log_dir="50.cd_hmm_tied",
    ),
    TrainingStep(
        script="90.deleted_interpolation/deleted_interpolation.pl",
    ),
]


def check_artifacts(
        step: TrainingStep,
        model_dir: Path,
        db_name: str
) -> list[str]:
    """
    veryify step artifacts arent empty and they exist
    returns list of errors.
    """
    errors = []
    for tmpl in step.artifacts:
        artifact = model_dir / tmpl.format(db=db_name)
        if not artifact.is_file():
            errors.append(f"  missing: {artifact}")
        elif artifact.stat().st_size == 0:
            errors.append(f"  empty: {artifact}")
    return errors


def check_logs(
        step: TrainingStep,
        log_dir: Path
) -> tuple[list[str], list[str]]:
    """
    check logs for warnings and errors
    returns (fatals, warnings) each being a list of error/warning strings
    """
    if not step.log_dir:
        return ([], [])
    subdir = log_dir / step.log_dir
    if not subdir.is_dir():
        return ([], [])

    fatals = []
    warnings = []
    for log_file in sorted(subdir.glob("*.log")):
        try:
            lines = log_file.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for lineno, line, in enumerate(lines, 1):
            hit = f"  {log_file.name}:{lineno}: {line.strip()}"
            if any(pat in line for pat in step.fatal_patterns):
                fatals.append(hit)
            elif any(pat in line for pat in step.warning_patterns):
                warnings.append(hit)
    return fatals, warnings


def print_failure_logs(step: TrainingStep, log_dir: Path, tail_lines: int = 20):
    """print relevant logs when a step exits with non zero error code"""
    if not step.log_dir:
        return
    subdir = log_dir / step.log_dir
    if not subdir.is_dir():
        return

    step_short = step.log_dir.split(".")[-1]
    for summary_log in sorted(subdir.glob(f"*.{step_short}.log")):
        lines = summary_log.read_text(errors="replace").splitlines()
        print(f"\n--- {summary_log.name} (last {tail_lines} lines) ---")
        print("\n".join(lines[-tail_lines:]))


def validate_step(
        step: TrainingStep,
        exp_dir: Path,
        db_name: str,
        log_dir: Path
):
    """
    check artifact errors and log error messages for a step
    """
    artifact_errors = check_artifacts(
        step,
        exp_dir / "model_parameters",
        db_name
    )
    if artifact_errors:
        print(
            f"[ERROR] {step.name} returned 0 "
            "but expected output is missing or empty:"
        )
        for msg in artifact_errors:
            print(msg)
        sys.exit(1)

    fatals, warnings = check_logs(step, log_dir)

    if warnings:
        print(f"[WARNING] {step.name} produced warning strings in logs:")
        for msg in warnings:
            print(msg)

    if fatals:
        print(
            f"[FATAL] {step.name} returned 0 but "
            "critical errors found in logs:"
        )
        for msg in fatals:
            print(msg)
        sys.exit(1)


def run_step(
        step: TrainingStep,
        scripts_dir: Path,
        exp_dir: Path,
        db_name: str,
        log_dir: Path
):
    """
    run sphinxtrain training step (perl) and check for errors
    """
    print(f"\n=== {step.name} ===")
    step_start = time.monotonic()
    ret = subprocess.call(["perl", str(scripts_dir / step.script)])
    elapsed = time.monotonic() - step_start
    minutes, seconds = divmod(int(elapsed), 60)
    print(f"=== Step time: {minutes}m {seconds}s ===")
    if ret != 0:
        # MLLT exits on 1 on convergence warning even with a valid transform
        # so check if the artifacts exist, and if they do ouput a warning
        # instead of step failure
        artifact_errors = check_artifacts(
            step,
            exp_dir / "model_parameters",
            db_name
        )
        if not artifact_errors:
            print(
                f"[WARNING] {step.name} exited {ret} "
                "but artifacts are present, continuing."
            )
        else:
            print(f"Error: {step.name} failed (exit {ret})")
            print_failure_logs(step, log_dir)
            sys.exit(ret)
    validate_step(step, exp_dir, db_name, log_dir)
    return elapsed


def resolve_mllt_seed(experiment: dict) -> int | None:
    """
    resolve mllt_init from experiment config to a seed value
    returns the seed or None for eye
    """
    pipeline_options = experiment.get("pipeline", {})
    mllt_init = pipeline_options.get("mllt_init", "eye")
    if mllt_init == "eye":
        return None
    if mllt_init == "random":
        return random.randint(0, 2**31 -1)
    try:
        return int(mllt_init)
    except (ValueError, TypeError):
        print(
            f"[WARNING] invalid mllt_init value '{mllt_init}', "
            "falling back to eye"
        )
        return None


def main():
    """program entry"""
    parser = argparse.ArgumentParser(description="Run sphinxtrain training.")
    parser.add_argument("exp_dir", type=Path)
    parser.add_argument(
        "--from-step",
        metavar="STEP",
        help="resume from step (e.g. '30.cd_hmm_untied' or '30')",
    )
    args = parser.parse_args()

    root = get_sphinx_root()
    exp_dir = args.exp_dir
    if not exp_dir.is_absolute():
        exp_dir = root / exp_dir

    db_name = exp_dir.name
    scripts_dir = root / "vendor" / "sphinxtrain" / "scripts"
    log_dir = exp_dir / "logdir"
    os.chdir(exp_dir)

    experiment = load_experiment(exp_dir, root)

    # set MLLT seed
    mllt_seed = resolve_mllt_seed(experiment)
    if mllt_seed is not None:
        os.environ["SPHINXASR_MLLT_SEED"] = str(mllt_seed)
        print(f"MLLT seed: {mllt_seed}")
    else:
        os.environ.pop("SPHINXASR_MLLT_SEED", None)
        print("MLLT init: eye (deterministic)")

    steps = STEPS
    if args.from_step:
        matches = [s for s in STEPS if args.from_step in s.name]
        if not matches:
            print(f"[ERROR] no step matching '{args.from_step}'")
            print("Available steps:")
            for s in STEPS:
                print(f"  {s.name}")
            sys.exit(1)
        start_idx = STEPS.index(matches[0])
        steps = STEPS[start_idx:]
        print(f"Resuming from: {matches[0].name}")

    total_start = time.monotonic()
    step_times: dict[str, float] = {}
    for step in steps:
        elapsed = run_step(step, scripts_dir, exp_dir, db_name, log_dir)
        step_times[step.name] = elapsed
    total_elapsed = time.monotonic() - total_start
    hours, remainder = divmod(int(total_elapsed), 3600)
    minutes, seconds = divmod(remainder, 60)

    print(f"\nTraining complete. Total time: {hours}h {minutes}m {seconds}s")

    #TODO write results.yml with step times


if __name__ == "__main__":
    main()
