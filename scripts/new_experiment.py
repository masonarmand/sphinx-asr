#!/usr/bin/env python3
"""
Create a new experiment directory with a config template.
TODO: Wiki page stuff

Usage:
    new_experiment.py   use default template
    new_experiment.py -- template <corpus_name> use corpus-specific template
    new_experiment.py --list    list available corpora
"""

from dataclasses import dataclass
import argparse
import shutil
import sys
import os
from pathlib import Path

# TODO media wiki stuff

# TODO maybe get_sphinx_root and err can live in a different util.py file
# or something

@dataclass
class Corpus:
    """Used for corpus list"""
    name: str
    has_template: bool

@dataclass
class CorpusTemplate:
    """Corpus template name and path."""
    path: Path
    label: str


def err(msg: str):
    """print error message to stderr and exit"""
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def get_sphinx_root() -> Path:
    """Get the project root directory."""
    root = os.environ.get("SPHINX_ROOT")
    if not root:
        err("SPHINX_ROOT environment variable not set. Exiting.")
    return Path(root)
    #return Path(__file__).resolve().parent.parent


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
) -> CorpusTemplate | None:
    """Get corpus template for path (if exists)."""
    if not corpus_path.is_dir():
        return None

    if not template_name:
        return CorpusTemplate(path=default_path, label="generic")

    template_path = corpus_path / "experiment.yml.template"
    template_label = ""
    if template_path.is_file():
        template_label = template_name
    else:
        template_path = default_path
        template_label = f"generic (no template found for {template_name}"

    return CorpusTemplate(path=template_path, label=template_label)


def make_experiment_dir(
        num: int,
        exp_dir: Path,
        root_dir: Path,
        config_template: CorpusTemplate):
    """Create the experiment directory."""
    exp_name = f"{num:03d}"
    exp_subdir = exp_dir / exp_name
    exp_subdir.mkdir(parents=True, exists_ok=True)
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
    # TODO idk if these path names should be hardcoded.
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
    config_template = get_corpus_template(
        args.template,
        root_template,
        corpus_dir / args.template)

    if not config_template.path.is_file():
        err("template not found at {config_template.path}")

    # make exp directory
    num = next_experiment_number(experiments_dir)
    make_experiment_dir(num, experiments_dir, root, config_template)


if __name__ == "__main__":
    main()
