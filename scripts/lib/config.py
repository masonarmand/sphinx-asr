"""
Configuration for sphinx-asr.

reads experiment.yml and corpus.yml files, resolves references, and generates
a valid sphinx_train.cfg for sphinxtrain.
"""

import platform
import re
import sys
from pathlib import Path

from .asr_util import (err, get_sphinx_root)

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
    return data


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
    """
    Load experiment.yml and resolve corpus references.

    each corpus entry in train.corpora and decode.corpus gets a '_corpus' key
    with the corpus.yml data. Split names are validated against the corpus.
    """
    exp_yml = exp_dir / "experiment.yml"
    if not exp_yml.is_file():
        raise FileNotFoundError(f"experiment.yml not found at {exp_yml}")

    experiment = load_yaml(exp_yml)

    # resolve training corpus references
    for entry in experiment.get("train", {}).get("corpora", []):
        corpus = load_corpus(entry["name"], sphinx_root)
        _validate_split(entry["name"], entry["split"], corpus)
        entry["_corpus"] = corpus

    # resolve decode corpus reference
    decode_corpus = experiment.get("decode", {}).get("corpus", {})
    if decode_corpus and decode_corpus.get("name"):
        corpus = load_corpus(decode_corpus["name"], sphinx_root)
        _validate_split(decode_corpus["name"], decode_corpus["split"], corpus)
        decode_corpus["_corpus"] = corpus

    return experiment


def generate_sphinx_train_cfg(
        exp_dir: Path,
        experiment: dict,
        sphinx_root: Path
) -> str:
    """TODO"""
    return ""

##############################################################################
# Internal helpers
##############################################################################

def _validate_split(corpus_name: str, split_name: str, corpus: dict):
    """Raise ValueError if split doesn't exist in corpus."""
    splits = corpus.get("splits", {})
    if split_name not in splits:
        available = ", ".join(splits.keys())
        raise ValueError(
            f"Split '{split_name}' not found in corpus '{corpus_name}'. "
            f"Available: {available}"
        )
