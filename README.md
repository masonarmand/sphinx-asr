# sphinx-asr

## Useful Resources
- [Sphinx-3 Decoder](https://www.cs.cmu.edu/~archan/s_info/Sphinx3/doc/s3_description.html)
- [The Incomplete Guide to Sphinx-3 Performance Tuning](https://cmusphinx.github.io/wiki/decodertuning/)

## TODO
- [X] Replace Dockerfile with a simple makefile? (now that im simplifying things, i realize
that we prob dont need docker because CMU sphinx tools have like zero dependencies. its just
raw C)
- [ ] Documentation
  - [ ] README
  - [ ] Documentation/comments in default `experiment.yml`
- [ ] Setup guide & usage
- [ ] Style guide for python & bash so codebase stays consisten in the future
- [ ] Scripts that accomplis the following:
  - [X] make exp dir
  - [X] functions to generate `sphinx_train.cfg` from yaml
  - [X] setup exp dir
  - [X] run train
  - [ ] decode train
  - [ ] gen feats
  - [ ] ensure everything works on both:
    - [ ] local machine
    - [ ] torque queue
- [ ] Config
  - [ ] find out what default config params should be included in `experiment.yml` for:
    - [ ] default
    - [ ] librispeech
    - [ ] switchboard
- [ ] Parser
  - [ ] librispeech parser/setup (call sphinxtrains internal included scripts)
  - [ ] Switchboard parser/setup script
- [X] Script for creating a corpus directory (creates yaml files and directory structure)
- [ ] genfeats once per corpus instead of per experiment
