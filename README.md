# sphinx-asr

## TODO
- [ ] make experiments/sub experiment dirs match whats currently in use
- [ ] make `sphinx new` create a wiki entry (if prof allows)
  - [ ] Maybe also optionally upload results of training/decoding to wiki entry automatically
  - [ ] wiki bot credentials and other stuff could go in config.yml (gitignored)
- [ ] ensure everything works with NFS queue and torque
- [ ] document `sphinxtrain` parameters somewhere

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
run it manually `./script.sh` (assuming you are under the repo folder), or you
can add a symlink to the script by running:
```
sudo make link
```
in which case you would be able to just run `sphinx` from anywhere.

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

