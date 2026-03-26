#!/usr/bin/env python3
"""
Create a new experiment directory with a config template.
TODO: Wiki page stuff

Usage:
    new_experiment.py   use default template
    new_experiment.py -- template <corpus_name> use corpus-specific template
    new_experiment.py --list    list available corpora
"""

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from lib.asr_util import err, get_sphinx_root

# TODO media wiki stuff

@dataclass
class Corpus:
    """Used for corpus list"""
    name: str
    has_template: bool

@dataclass
class ConfigTemplate:
    """Corpus template name and path."""
    path: Path
    label: str


def get_corpora_list(corpus_dir: Path) -> list[Corpus]:
    """Find all corpora that have a corpus.yml file."""
    corpora = []
    if not corpus_dir.is_dir():
        return corpora
    for path in sorted(corpus_dir.iterdir()):
        if path.is_dir() and (path / "corpus.yml").is_file():
            has_template = (path / "experiment.yml.template").is_file()
            corpora.append(Corpus(path.name, has_template))
    return corpora


def next_experiment_number(experiments_dir: Path) -> int:
    """Find the next available experiment number."""
    if not experiments_dir.is_dir():
        return 1
    existing = []
    for path in experiments_dir.iterdir():
        try:
            existing.append(int(path.name))
        except ValueError:
            continue
    return max(existing, default=0) + 1


def print_corpora_list(corpora_list: list[Corpus], templates_only=False):
    """Prints a Corpus list"""
    print("Available corpora:")
    for corpus in corpora_list:
        if not corpus.has_template and templates_only:
            continue
        marker = " (template available)" if corpus.has_template else ""
        print(f"  {corpus.name}{marker}")


def get_corpus_template(
        template_name: str | None,
        default_path: Path,
        corpus_path: Path
) -> ConfigTemplate | None:
    """Get corpus template for path (if exists)."""
    if not corpus_path.is_dir():
        return None

    if not template_name:
        return ConfigTemplate(path=default_path, label="generic")

    template_path = corpus_path / "experiment.yml.template"
    template_label = ""
    if template_path.is_file():
        template_label = template_name
    else:
        template_path = default_path
        template_label = f"generic (no template found for {template_name}"

    return ConfigTemplate(path=template_path, label=template_label)


def make_experiment_dir(
        num: int,
        exp_dir: Path,
        root_dir: Path,
        config_template: ConfigTemplate):
    """Create the experiment directory."""
    exp_name = f"{num:03d}"
    exp_subdir = exp_dir / exp_name
    exp_subdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config_template.path, exp_subdir / "experiment.yml")
    rel_dir = exp_subdir.relative_to(root_dir)
    print(f"Created experiment {exp_name} at {rel_dir}/")
    print(f"  Template: {config_template.label}")


def main():
    """Program entry."""
    parser = argparse.ArgumentParser(
        description="Create a new experiment directory with a config template."
    )
    parser.add_argument(
        "-t", "--template",
        metavar="CORPUS",
        help="use the experiment template from a specific corpus",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        dest="list_corpora",
        help="list available corpora"
    )
    args = parser.parse_args()

    root = get_sphinx_root()
    corpus_dir = root / "corpus"
    experiments_dir = root / "experiments"
    root_template = root / "experiment.yml.template"
    corpora = get_corpora_list(corpus_dir)

    # list
    if args.list_corpora:
        if not corpora:
            err("No corpora found in corpus/")
        print_corpora_list(corpora)
        sys.exit(0)

    # template
    if args.template:
        config_template = get_corpus_template(
            args.template,
            root_template,
            corpus_dir / args.template)
    else:
        config_template = ConfigTemplate(path=root_template, label="generic")

    if not config_template.path.is_file():
        err("template not found at {config_template.path}")

    # make exp directory
    num = next_experiment_number(experiments_dir)
    make_experiment_dir(num, experiments_dir, root, config_template)


if __name__ == "__main__":
    main()
