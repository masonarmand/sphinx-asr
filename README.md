# sphinx-asr

## TODO
- [ ] Documentation
  - [ ] README
  - [ ] Documentation/comments in default `experiment.yml`
- [ ] Setup guide & usage
- [ ] Style guide for python & bash so codebase stays consisten in the future
- [ ] Scripts that accomplis the following:
  - [ ] make exp dir
  - [ ] functions to generate `sphinx_train.cfg` from yaml
  - [ ] setup exp dir
  - [ ] run train
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
