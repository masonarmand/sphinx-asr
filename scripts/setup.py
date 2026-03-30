#!/usr/bin/env python3
"""
Set up a sphinxtrain experiment from experiment.yml

does the following:
    - creates directory structure
    - generates:
        - fileids
        - transcriptions
        - dictionary
        - phone list
        - filler dictionary
        - feat.params
        - sphinx_train.cfg

Usage:
    setup.py <experiment_dir>
"""

import argparse
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from lib.asr_util import get_sphinx_root
from lib.config import generate_sphinx_train_cfg, load_experiment

from corpus import get_adapter


@dataclass
class Dictionary:
    """Result of building a pruned dictionary from a master lexicon"""
    entries: list[str]
    phones: set[str]
    oov: set[str] # words not found in lexicon

    @staticmethod
    def build(lexicon_path: Path, words: set[str]) -> "Dictionary":
        """Build pruned dictioanry from master lexicon"""
        stress_re = re.compile(r"\d$")  # strip the stress numbers

        available = {}
        with open(lexicon_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                fields = line.split()
                if len(fields) < 2:
                    continue

                word = fields[0]
                phones = fields[1:]

                if word not in available:
                    available[word] = []
                available[word].append(phones)

        entries = []
        phones = set()
        oov = set()

        for word in sorted(words):
            if word in available:
                for i, raw_phones in enumerate(available[word]):
                    clean = [stress_re.sub("", p) for p in raw_phones]
                    phones.update(clean)
                    entry_word = word if i == 0 else f"{word}({i + 1})"
                    entries.append(f"{entry_word} {' '.join(clean)}")
            else:
                oov.add(word)

        return Dictionary(entries=entries, phones=phones, oov=oov)


def _resolve_dict_path(experiment: dict, root: Path) -> Path | None:
    """Resolve dictionary path"""
    # experiment.yml override
    explicit = experiment.get("train", {}).get("dict")
    if explicit:
        path = root / explicit
        if path.is_file():
            return path
        print(f"  Warning: explicit dict not found: {path}")

    # corpus default
    train_corpora = experiment.get("train", {}).get("corpora", [])
    if train_corpora:
        corpus = train_corpora[0].get("_corpus", {})
        dict_rel = corpus.get("dict", "")
        if dict_rel:
            path = corpus["_dir"] / dict_rel
            if path.is_file():
                return path
    return None


def filter_oov_utterances(
        exp_dir: Path,
        db_name: str,
        oov: set[str],
        prefix: str
) -> int:
    """
    remove utterances containing OOV words from fileids and transcription.
    this avoids the need to use G2P for automatically generating pronunciations
    for words not in the dictionary.
    oov = Out Of Vocabulary
    returns count of removed utterances.
    """
    fileids_path = exp_dir / "etc" / f"{db_name}_{prefix}.fileids"
    trans_path = exp_dir / "etc" / f"{db_name}_{prefix}.transcription"

    if not fileids_path.is_file():
        return 0

    fileids = fileids_path.read_text().splitlines()
    trans = trans_path.read_text().splitlines()

    kept_fileids = []
    kept_trans = []
    removed = 0

    for fid, tr, in zip(fileids, trans):
        words = tr.split("</s>")[0].split("<s>")[-1].split()
        if oov.isdisjoint(words):
            kept_fileids.append(fid)
            kept_trans.append(tr)
        else:
            removed += 1

    fileids_path.write_text("\n".join(kept_fileids) + "\n")
    trans_path.write_text("\n".join(kept_trans) + "\n")

    return removed


def generate_dictionary(
        exp_dir: Path,
        db_name: str,
        experiment: dict,
        root: Path,
        words: set[str]):
    """Build pruned dictionary, phone list, and filler dictionary."""
    train_corpora = experiment.get("train", {}).get("corpora", [])

    # exlude filler words from main dict
    filler_words = {"<s>", "</s>", "<sil>"}
    for entry in train_corpora:
        for word in entry["_corpus"].get("fillers", {}).keys():
            filler_words.add(word)
    words = words - filler_words

    print(f"Building dictionary ({len(words)} unique words)...")
    dict_path = _resolve_dict_path(experiment, root)

    if dict_path is None:
        print("  Warning: no dictionary found, skipping dict/phone/filler generation")
        return

    print(f"  Lexicon: {dict_path}")
    dictionary = Dictionary.build(dict_path, words)

    # save pruned dictionary
    dic_file = exp_dir / "etc" / f"{db_name}.dic"
    with open(dic_file, "w") as f:
        for entry in dictionary.entries:
            f.write(f"{entry}\n")
    print(f"  Written: {dic_file.name} ({len(dictionary.entries)} entries)")

    # save OOV words
    if dictionary.oov:
        oov_file = exp_dir / "etc" / f"{db_name}_train.oov"
        with open(oov_file, "w") as f:
            for word in sorted(dictionary.oov):
                f.write(f"{word}\n")
        print(
            f"  Warning: {len(dictionary.oov)} words not in dictionary, "
            f"written to {oov_file.name}")

        train_removed = filter_oov_utterances(exp_dir, db_name, dictionary.oov, "train")
        decode_removed = filter_oov_utterances(exp_dir, db_name, dictionary.oov, "decode")
        if train_removed or decode_removed:
            print(
                f"  Filtered {train_removed} train, "
                f"{decode_removed} decode utterances with OOV words"
            )

    # save phone list
    dictionary.phones.add("SIL")
    # corpus specific fillers:
    for entry in train_corpora:
        for phone in entry["_corpus"].get("fillers", {}).values():
            dictionary.phones.add(phone)

    phone_file = exp_dir / "etc" / f"{db_name}.phone"
    with open(phone_file, "w") as f:
        for phone in sorted(dictionary.phones):
            f.write(f"{phone}\n")
    print(f"  Written: {phone_file.name} ({len(dictionary.phones)} phones)")

    # save filler dictionary
    filler_file = exp_dir / "etc" / f"{db_name}.filler"
    with open(filler_file, "w") as f:
        f.write("<s> SIL\n")
        f.write("</s> SIL\n")
        f.write("<sil> SIL\n")
        # corpus specific fillers
        for entry in train_corpora:
            corpus_fillers = entry["_corpus"].get("fillers", {})
            for word, phone in corpus_fillers.items():
                f.write(f"{word} {phone}\n")
    print(f"  Written: {filler_file.name}")


def setup_directories(exp_dir: Path):
    """Create the SphinxTrain directory structure."""
    print("creating directory structure...")
    dir_list = [
        "etc", "feat", "logdir", "bwaccumdir",
        "model_parameters", "model_architecture",
        "qmanager", "result", "presult"
    ]
    for d in dir_list:
        (exp_dir / d).mkdir(parents=True, exist_ok=True)


def generate_utterances(
        exp_dir: Path,
        db_name: str,
        experiment: dict
) -> set[str]:
    """
    Generate fileids and transcription files for training and decoding
    returns union of all words seen across both sets
    """
    train_words = generate_train_utterances(exp_dir, db_name, experiment)
    decode_words = generate_decode_utterances(exp_dir, db_name, experiment)
    return train_words | decode_words


def generate_train_utterances(
        exp_dir: Path,
        db_name: str,
        experiment: dict
) -> set[str]:
    """Generate training fileids and transcription files"""
    print("Generating training fileids and transcriptions...")
    words = set()

    fileids_path = exp_dir / "etc" / f"{db_name}_train.fileids"
    trans_path = exp_dir / "etc" / f"{db_name}_train.transcription"

    with open(fileids_path, "w") as fids, open(trans_path, "w") as trans:
        for entry in experiment.get("train", {}).get("corpora", []):
            corpus_data = entry["_corpus"]
            split_cfg = corpus_data["splits"][entry["split"]]

            print(f"  {entry['name']}/{entry['split']}...")
            adapter = get_adapter(entry["name"])
            count = 0

            adapter_utt = adapter.get_utterances(
                corpus_data["_dir"],
                entry["split"],
                split_cfg,
                corpus_data
            )
            for fileid, text in adapter_utt:
                fids.write(f"{fileid}\n")
                trans.write(f"<s> {text} </s> ({fileid})\n")
                words.update(text.split())
                count += 1
            print(f"    {count} utterances")
    return words

def generate_decode_utterances(
        exp_dir: Path,
        db_name: str,
        experiment: dict
) -> set[str]:
    """Generate decode fileids and transcription files"""
    print("Generating decode fileids and transcriptions...")
    words = set()
    decode_cfg = experiment.get("decode", {}).get("corpus", {})

    if not decode_cfg or not decode_cfg.get("name"):
        return words

    corpus_data = decode_cfg["_corpus"]
    split_name = decode_cfg["split"]
    split_cfg = corpus_data["splits"][split_name]

    adapter = get_adapter(decode_cfg["name"])
    count = 0
    fileids_path = exp_dir / "etc" / f"{db_name}_decode.fileids"
    trans_path = exp_dir / "etc" / f"{db_name}_decode.transcription"
    with open(fileids_path, "w") as fids, open(trans_path, "w") as trans:
        adapter_utt = adapter.get_utterances(
            corpus_data["_dir"],
            split_name,
            split_cfg,
            corpus_data
        )
        for fileid, text in adapter_utt:
            fids.write(f"{fileid}\n")
            trans.write(f"<s> {text} </s> ({fileid})\n")
            words.update(text.split())
            count += 1
    print(f"  {decode_cfg['name']}/{split_name}: {count} utterances")

    return words


def generate_feat_params(exp_dir: Path, experiment: dict, root: Path):
    """Generate feat.params with actual values from corpus config"""
    src = root / "vendor" / "sphinxtrain" / "etc" / "feat.params"
    dst = exp_dir / "etc" / "feat.params"

    if not src.is_file():
        print(f"Warning: feat.params not found at {src}")
        return

    content = src.read_text()

    train_corpora = experiment.get("train", {}).get("corpora", [])
    if train_corpora:
        primary = train_corpora[0].get("_corpus", {})
    else:
        primary = {}

    replacements = {
        "__CFG_LO_FILT__": str(primary.get("lo_filt", 130)),
        "__CFG_HI_FILT__": str(primary.get("hi_filt", 6800)),
        "__CFG_NUM_FILT__": str(primary.get("num_filt", 25)),
        "__CFG_TRANSFORM__": "dct",
        "__CFG_LIFTER__": "22",
        "__CFG_FEATURE__": "1s_c_d_dd",
        "__CFG_AGC__": "none",
        "__CFG_CMN__": primary.get("cmn", "live"),
        "__CFG_VARNORM__": "no",
        "__CFG_WAVFILE_SRATE__": str(int(primary.get("sample_rate", 16000)))
    }

    # if users set CFG_SVSPEC, then set svspec to that in feat.params,
    # otherwise just remove it
    svspec = experiment.get("sphinxtrain", {}).get("CFG_SVSPEC", "")
    if svspec:
        content = content.replace("__CFG_SVSPEC__", svspec)
    else:
        content = re.sub(r"^-svspec\s.*\n?", "", content, flags=re.MULTILINE)

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    dst.write_text(content)
    print("Generated feat.params")


def generate_config(exp_dir: Path, experiment: dict, root: Path):
    """Generate sphinx_train.cfg from experiment config."""
    print("Generating sphinx_train.cfg...")
    cfg = generate_sphinx_train_cfg(exp_dir, experiment, root)
    cfg_file = exp_dir / "etc" / "sphinx_train.cfg"
    cfg_file.write_text(cfg)
    print(f"  Written: {cfg_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Set up a SphinxTrain experiment from experiment.yml."
    )
    parser.add_argument(
        "exp_dir",
        type=Path,
        help="Path to the experiment directory (e.g. experiments/001)",
    )
    args = parser.parse_args()

    root = get_sphinx_root()
    exp_dir = args.exp_dir
    if not exp_dir.is_absolute():
        exp_dir = root / exp_dir

    db_name = exp_dir.name

    print(f"Loading experiment from {exp_dir}/experiment.yml")
    experiment = load_experiment(exp_dir, root)

    setup_directories(exp_dir)
    words = generate_utterances(exp_dir, db_name, experiment)
    generate_dictionary(exp_dir, db_name, experiment, root, words)
    generate_feat_params(exp_dir, experiment, root)
    generate_config(exp_dir, experiment, root)
    print(f"\nSetup complete for experiment {db_name}.")


if __name__ == "__main__":
    main()
