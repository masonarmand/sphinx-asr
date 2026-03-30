# sphinx-asr
Sphinx Automatic Speech Recognition. This repo contains a set of scripts & utilities that serve as wrappers around CMU SphinxTrain and CMU PocketSphinx.

## TODO
### General
- [ ] Multi-Corpora training + corpus compatibilty verification
- [X] `train.py` - show warnings & errors from logs automatically
- [ ] `config.yml` (root config) - number of jobs, enable/disable torque, wiki credentials
### Feature Parity with old system
- [ ] MediaWiki
- [ ] WER scoring
- [ ] MLLR speaker adaptation `sphinx adapt <exp> <speaker>` `sphinx decode --mllr`
- [ ] MLLT seed control. Set `mllt_seed` to number or `random` in `experiment.yml`
  - maybe an optional `mllt_trials: N` to run N seeds and keep the best.
- [ ] `sphinx status` show running/queued jobs
- [ ] `sphinx info <corpus> <split>` hours, utterance count, OOV
- [ ] `sphinx new --from <exp>` create new expr but symlink a trained model from other experiment
- [X] `sphinx train --from-step <N>` resume from a specific step without starting over
### New features (?)
- [ ] `results.yml` - train & decode results.
  - train
    - time completed
    - total time
    - time for each step
  - decode
    - time completed
    - total time
    - WER
    - counts for sentences/words/insertions/deletions/substitutions
- [ ] `sphinx compare <exp1> <exp2> - diff the WER, config params, training time
- [ ] `sphinx search` search experiments by name, author, description, corpora, etc
- [ ] `sphinx clean <exp>` delete training artifacts but keep final model (to save on disk space).

## Usage cheatsheet
```
Usage: sphinx.sh <command> [args]

Commands:
  new [-t CORPUS] [-l]
  setup <exp_dir>
  feats <corpus> <split> 
  train <exp_dir>
  decode <exp_dir>      
```

Example of the full pipeline:
```
# list available corpus templates
sphinx new --list

# create a numbered experiment dir
sphinx new --template librispeech

# edit the config parameters in editor of your choice
nano experiments/001/experiment.yml

# setup experiment
sphinx setup experiments/001

# run a train
sphinx train experiments/001

# run a decode
sphinx decode experiments/001
```

## Setting up the project

### Dependencies

Packages required: python3, python3-venv, perl, sox, make, gcc, and cmake.
Also, sphinxtrain refers to `python3` as `python` so you will either need
a symlink linking python3 to python (if one does not exist already), or on 
ubuntu you could install:
```
sudo apt install python-is-python3
```

Ubuntu/Debian
```
sudo apt install build-essential cmake python3 python3-venv perl sox
```

Fedora/RHEL
```
sudo dnf install gcc gcc-c++ cmake python3 python3-devel perl sox
```

macOS
```
brew install cmake sox
```

### Building
`sphinx-asr` uses `SphinxTrain` for training and `PocketSphinx` for decoding.
To build these run:
```
make
```
This will output the binaries under `bin/<your-computer-architecture>` (which in
most scenarios would be `bin/x86_64`.

### sphinx.sh
This script is the only script you will have to interact with. You can either
run it manually `./sphinx.sh` (assuming you are under the repo folder), or you
can add a symlink to the script by running:
```
sudo make link
```
in which case you would be able to just run `sphinx` (without the `.sh`) from anywhere.

### Corpora
The corpora are stored under the `corpus/` directory. Each corpus has the following
directory structure:
```
corpus/
  corpus_name/
    corpus.yml
    experiment.yml.template
    dict/
    lm/
    <corpus specific files>
```
- `corpus.yml`: contains information about the corpus and info about each of the splits
- `experiment.yml.template`: Corpus-specific experiment template configuration file
- `dict/`: Folder containing lexicons/dictionaries
- `lm`: Folder containing language models

Use `sphinx feats` to generate feats for a corpus (the .mfc files).
```
sphinx feats librispeech dev-clean # generates feats for dev-clean split 
                                   # under librispeech
sphinx feats librispeech all # generates feats for all splits under the
                             # librispeech corpus.
```

Each corpus usually has its own format, so a parser must be created for
each new corpus to convert the format into something that is readable by
sphinxtrain. See `scripts/corpus` for corpus-specific parsers.

## Experiments

### 1. Creating a new experiment
run: 
```
sphinx new
```
This will create a numbered experiment directory under `experiments/` using
the default template. If you would like to use a corpus template pass the `-t` or 
`--template` argument. E.g for librispeech:
```
sphinx new -t librispeech
```

### 2. Modifying experiment.yml
experiment.yml defines the following:
- experiment name
- experiment author
- what corpora & splits to train on
- what corpus split to decode on
- `sphinx_train.cfg` parameter overrides.

The experiment configuration allows you to list multiple corpora and multiple splits
for training.  
Example:
```
train:
  corpora:
    - name: librispeech
      splits:
      - train-clean-100
      - train-clean-360
    - name: switchboard
      splits:
      - 145hr
      - 300hr
```

### 3. Setting up the experiment
run:
```
sphinx setup experiments/your-experiment-number
```
This will create the directory structure, as well as things like the `sphinx_train.cfg`
which is generated from your `experiment.yml`.

### 4. Training and Decoding
To run a train:
```
sphinx train experiments/your-experiment-number
```
To run a decode:
```
sphinx decode experiments/your-experiment-number
```

## Useful Resources
- [Sphinx-3 Decoder](https://www.cs.cmu.edu/~archan/s_info/Sphinx3/doc/s3_description.html)
- [The Incomplete Guide to Sphinx-3 Performance Tuning](https://cmusphinx.github.io/wiki/decodertuning/)

