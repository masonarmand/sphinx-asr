"""
General helper functions for sphinx-asr scripts.
"""
import os
import sys
from pathlib import Path

SPINNER_CHARS = ["|", "/", "-", "\\"]


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


def waitbar(current: int, total: int, label: str = "") -> str:
    """
    progress bar string. example:
        [=================>          ] 45/100 (45.0%) label
    """
    try:
        term_width = os.get_terminal_size().columns
    except OSError:
        term_width = 40

    suffix = f" {current}/{total} ({(current/total*100) if total else 0:.1f}%)"
    suffix += f" {label}" if label else ""
    bar_width = term_width - len(suffix) - 2
    bar_width = max(bar_width, 10)

    if total == 0:
        pct = 0.0
        filled = 0
    else:
        pct = current / total
        filled = int(bar_width * pct)

    bar = "=" * filled
    if filled < bar_width:
        bar += ">"
    bar = bar.ljust(bar_width)

    return f"\r[{bar}]{suffix}"


def spinner(idx: int, label: str = "") -> str:
    """build spinner string, for a loading animation"""
    char = SPINNER_CHARS[idx % len(SPINNER_CHARS)]
    suffix = f" {label}" if label else ""
    return f"\r{char}{suffix}"
