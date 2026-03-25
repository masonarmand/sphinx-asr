"""
Configuration for sphinx-asr.

reads experiment.yml and corpus.yml files, resolves references, and generates
a valid sphinx_train.cfg for sphinxtrain.
"""

import platform
import re
import sys
from pathlib import Path

from asr_util import (err, get_sphinx_root)

# TODO maybe we should have a requirements.txt and a venv, but idk i dont want
# to complicate things.
try:
    import yaml
except ImportError:
    err("PyYAML is required. Install with: pip install pyyaml")


def load_yaml(path: Path) -> dict:
    """Load a yaml file and return its contents."""
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise TypeError(f"Expected yaml mapping in {path}")


def load_corpus(corpus_name: str, sphinx_root: Path) -> dict:
    """
    Load corpus.yml for a given corpus (also adds _dir key with the resolved
    corpus path.
    """
    corpus_dir = sphinx_root / "corpus" / corpus_name
    corpus_yml = corpus_dir / "corpus.yml"

    if not corpus_yml.is_file():
        raise FileNotFoundError(
            f"corpus.yml not found for {corpus.name} at {corpus_yml}"
        )

    data = load_yaml(corpus_yml)
    data["_dir"] = corpus_dir
    return data


def load_experiment(exp_dir: Path, sphinx_root: Path) -> dict:
    """TODO"""
    return {}

def generate_sphinx_train_cfg(
        exp_dir: Path,
        experiment: dict,
        sphinx_root: Path
) -> str:
    """TODO"""
    return ""



