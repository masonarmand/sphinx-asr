"""
General helper functions for sphinx-asr scripts.
"""
import os
import sys
from pathlib import Path


def err(msg: str):
    """Print error message to stderr and exit."""
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def get_sphinx_root() -> Path:
    """Get the project root directory."""
    root = os.environ.get("SPHINX_ROOT")
    if not root:
        err("SPHINX_ROOT environment variable not set. Exiting.")
    return Path(root)
