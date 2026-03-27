#!/bin/sh
# entry point for sphinx-asr
# see usage() function for usage.
#
# On a torque cluster, scripts are submitted as jobs.
# On a local machine they run directly.

set -e

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -f "$VENV_DIR/bin/python3" ]; then
    echo "Creating python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Installing python dependencies (this is a one time setup)..."
    "$VENV_DIR/bin/pip" install -r requirements.txt
fi

PYTHON="$VENV_DIR/bin/python3"
ARCH="$(uname -m)"
export SPHINX_ROOT="$SCRIPT_DIR"
export PATH="$SCRIPT_DIR/bin/$ARCH:$PATH"

export SPHINXTRAIN_DIR="$SCRIPT_DIR/vendor/sphinxtrain"
export SPHINXTRAIN_BIN_DIR="$SCRIPT_DIR/bin/$ARCH"

COMMAND="${1:-}"
[ $# -gt 0 ] && shift

usage() {
    echo "Usage: sphinx.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  new [-t CORPUS] [-l] Create a new experiment (default template, or specify corpus)"
    echo "  setup <exp_dir>        Generate sphinxtrain files from experiment.yml"
    echo "  train <exp_dir>        Run training"
    echo "  decode <exp_dir>       Run decoding"
    echo "  feats <corpus> <split> Extract features (once per corpus split)"
    echo "  lm <corpus> <split>    build a trigram language model from training transcripts"
    exit 1
}

# run a script locally or via torque
# TODO idk if the torque stuff works, it is untested for now
run_script() {
    script="$1"
    shift

    # check if qsub command exists
    # TODO maybe add a flag to overwrite this and force no torque
    if command -v qsub >/dev/null 2>&1; then
        echo "submitting job to torque queue..."
        qsub -v SPHINX_ROOT="$SPHINX_ROOT",SPHINX_CMD="$script",SPHINX_ARGS="$*" \
            "$SCRIPT_DIR/scripts/sphinx_job.sh"
    else
        $PYTHON "$SCRIPT_DIR/scripts/$script" "$@"
    fi
}

case "$COMMAND" in
    new)
        $PYTHON "$SCRIPT_DIR/scripts/new_experiment.py" "$@"
        ;;
    setup)
        $PYTHON "$SCRIPT_DIR/scripts/setup.py" "$@"
        ;;
    train)
        run_script "train.py" "$@"
        ;;
    decode)
        run_script "decode.py" "$@"
        ;;
    feats)
        $PYTHON "$SCRIPT_DIR/scripts/feats.py" "$@"
        ;;
    lm)
        $PYTHON "$SCRIPT_DIR/scripts/lm.py" "$@"
        ;;
    *)
        usage
        ;;
esac
