#!/bin/sh
# entry point for sphinx-asr
# see usage() function for usage.
#
# On a torque cluster, scripts are submitted as jobs.
# On a local machine they run directly.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ARCH="$(uname -m)"
export SPHINX_ROOT="$SCRIPT_DIR"
export PATH="$SCRIPT_DIR/bin/$ARCH:$PATH"

export SPHINXTRAIN_DIR="$SCRIPT_DIR/vendor/sphinxtrain"
export SPHINXTRAIN_BIN_DIR="$SCRIPT_DIR/bin/$ARCH"

COMMAND="$1"
shift || true

usage() {
    echo "Usage: sphinx.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  new [-t CORPUS] [-l] Create a new experiment (default template, or specify corpus)"
    # TODO
    # - setup?
    # - feats? I think feats will run only if feats dont already exist
    # - train
    # - decode
    # - score (would be cool if score could output matplotlib graphs and stuff idk,
    #          maybe there would be a separate script for that)
    # - corpora - could list all available copora and splits?
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
        python3 "$SCRIPT_DIR/scripts/$script" "$@"
    fi
}

case "$COMMAND" in
    new)
        python3 "$SCRIPT_DIR/scripts/new_experiment.py" "$@"
        ;;
    setup)
        python3 "$SCRIPT_DIR/scripts/setup.py" "$@"
        ;;
    train)
        run_script "train.py" "$@"
        ;;
    feats)
        python3 "$SCRIPT_DIR/scripts/feats.py" "$@"
        ;;
    # TODO all the other sub-scripts
    *)
        usage
        ;;
esac
