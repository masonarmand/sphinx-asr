#!/usr/bin/env python3
"""
corpus adapter interface.

Each corpus has an adapter module in scripts/corpus that parses its specific
transcript format and directory layout. To add a new corpus format create a
file with the corpus name as the filename and implement get_utterances()
see scripts/corpus/librispeech.py as an example
"""

import importlib
from pathlib import Path


def get_adapter(corpus_name: str):
    """
    Load the corpus adapter module for a given corpus.

    looks for scripts/corpus/<corpus_name>.py and returns the module.
    module must implement this function:
    get_utterances(corpus_dir, split_name, split_cfg) -> Iterable[(str, str)]
    """
    try:
        return importlib.import_module(f"corpus.{corpus_name}")
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            f"No corpus adapter found for '{corpus_name}'. "
            f"Expected: scripts/corpus/{corpus_name}.py"
        )
