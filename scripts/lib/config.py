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
    raw_corpora = experiment.get("train", {}).get("corpora", [])
    expanded = []
    for entry in raw_corpora:
        corpus = load_corpus(entry["name"], sphinx_root)

        splits = entry.get("splits", [])
        if "split" in entry:
            splits.append(entry["split"])

        for split_name in splits:
            _validate_split(entry["name"], split_name, corpus)
            expanded.append({
                "name": entry["name"],
                "split": split_name,
                "_corpus": corpus
            })
    experiment["train"]["corpora"] = expanded

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
        sphinx_root: Path,
) -> str:
    """
    Generate sphinx_train.cfg content from experiment config.

    Reads the vendor sphinx_train.cfg template and applies:
    - path placeholders
    - corpus settings
    - audio directory
    - LM path
    - decode fileids/transcription paths
    - parameters from experiment.yml sphinxtrain
    """
    template_path = (
        sphinx_root / "vendor" / "sphinxtrain" / "etc" / "sphinx_train.cfg"
    )
    if not template_path.is_file():
        raise FileNotFoundError(
            f"sphinx_train.cfg template not found at {template_path}"
        )

    cfg = template_path.read_text()
    exp_dir = exp_dir.resolve()
    sphinx_root = sphinx_root.resolve()

    db_name = exp_dir.name
    sphinxtrain_dir = str(sphinx_root / "vendor" / "sphinxtrain")
    bin_dir = str(sphinx_root / "bin" / platform.machine())

    cfg = cfg.replace("___DB_NAME___", db_name)
    cfg = cfg.replace("___BASE_DIR___", str(exp_dir))
    cfg = cfg.replace("___SPHINXTRAIN_DIR___", sphinxtrain_dir)
    cfg = cfg.replace("___SPHINXTRAIN_BIN_DIR___", bin_dir)

    overrides = {}

    # audio settings
    train_corpora = experiment.get("train", {}).get("corpora", [])
    if train_corpora:
        primary = train_corpora[0].get("_corpus", {})
        overrides["CFG_WAVFILE_EXTENSION"] = primary.get(
            "audio_format", "wav"
        )
        overrides["CFG_WAVFILE_TYPE"] = primary.get("audio_type", "mswav")
        overrides["CFG_WAVFILE_SRATE"] = float(
            primary.get("sample_rate", 16000)
        )

    overrides["CFG_WAVFILES_DIR"] = str(sphinx_root)
    overrides["CFG_FEATFILES_DIR"] = str(sphinx_root)

    # LM path
    decode_cfg = experiment.get("decode", {})
    lm_path = _resolve_lm_path(decode_cfg, sphinx_root)
    if lm_path:
        overrides["DEC_CFG_LANGUAGEMODEL"] = lm_path

    overrides["DEC_CFG_LISTOFFILES"] = (
        f"{exp_dir}/etc/{db_name}_decode.fileids"
    )
    overrides["DEC_CFG_TRANSCRIPTFILE"] = (
        f"{exp_dir}/etc/{db_name}_decode.transcription"
    )

    user_overrides = experiment.get("sphinxtrain", {})
    if user_overrides:
        overrides.update(user_overrides)

    cfg = _apply_overrides(cfg, overrides)
    return cfg

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


def _resolve_lm_path(decode_cfg: dict, sphinx_root: Path) -> str | None:
    """
    resolve the language model path for decoding.
    """
    # experiment.yml override
    explicit_lm = decode_cfg.get("lm")
    if explicit_lm:
        return str(sphinx_root / explicit_lm)

    # corpus default
    corpus = decode_cfg.get("corpus", {}).get("_corpus")
    if corpus:
        lm_rel = corpus.get("lm", "")
        if lm_rel:
            return str(corpus["_dir"] / lm_rel)


def _apply_overrides(cfg: str, overrides: dict) -> str:
    """
    Replace values in sphinx_train.cfg.
    """
    for key, value in overrides.items():
        perl_value = _to_perl_value(value)

        # look for uncommented vars first
        pattern = re.compile(
            r"^(\s*\$" + re.escape(key) + r"\s*=\s*)(.+?)(;\s*(?:#.*)?)$",
            re.MULTILINE,
        )

        if pattern.search(cfg):
            cfg = pattern.sub(rf"\g<1>{perl_value}\g<3>", cfg)
            continue

        # look for commented out vars
        comment_pattern = re.compile(
            r"^(\s*)#\s*(\$"
            + re.escape(key)
            + r"\s*=\s*)(.+?)(;\s*(?:#.*)?)$",
            re.MULTILINE,
        )

        if comment_pattern.search(cfg):
            cfg = comment_pattern.sub(
                rf"\g<1>\g<2>{perl_value}\g<4>", cfg, count=1
            )

    return cfg


def _to_perl_value(value) -> str:
    """
    convert a python value to a perl string.
    """
    if isinstance(value, bool):
        return "'yes'" if value else "'no'"
    if isinstance(value, (int, float)):
        return str(value)

    s = str(value)

    # strings containing $ need double quotes
    if "$" in s:
        return f'"{s}"'

    # numeric strings (example: 1e-80)
    if re.match(r"^-?\d+\.?\d*(e[+-]?\d+)?$", s, re.IGNORECASE):
        return s

    # everything else is single quotes
    return f"'{s}'"
