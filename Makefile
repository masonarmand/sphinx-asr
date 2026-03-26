ARCH := $(shell uname -m)
PREFIX := bin/$(ARCH)

SPHINXTRAIN_SRC := vendor/sphinxtrain
POCKETSPHINX_SRC := vendor/pocketsphinx

SPHINXTRAIN_BUILD := $(SPHINXTRAIN_SRC)/build
POCKETSPHINX_BUILD := $(POCKETSPHINX_SRC)/build

.PHONY: all pocketsphinx sphinxtrain install clean

all: install

pocketsphinx:
	cmake -S $(POCKETSPHINX_SRC) -B $(POCKETSPHINX_BUILD)
	cmake --build $(POCKETSPHINX_BUILD)

sphinxtrain: pocketsphinx
	cmake -S $(SPHINXTRAIN_SRC) -B $(SPHINXTRAIN_BUILD)
	cmake --build $(SPHINXTRAIN_BUILD)

install: sphinxtrain
	mkdir -p $(PREFIX)
	find $(SPHINXTRAIN_BUILD) -maxdepth 1 -type f -executable -exec cp {} $(PREFIX)/ \;
	cp $(POCKETSPHINX_BUILD)/pocketsphinx $(PREFIX)/
	cp $(POCKETSPHINX_BUILD)/pocketsphinx_batch $(PREFIX)/
	cp $(POCKETSPHINX_BUILD)/pocketsphinx_lm_convert $(PREFIX)/

link:
	ln -sf $(CURDIR)/sphinx.sh /usr/local/bin/sphinx

unlink:
	rm -f /usr/local/bin/sphinx

clean:
	rm -rf $(SPHINXTRAIN_BUILD) $(POCKETSPHINX_BUILD)
	rm -rf $(PREFIX)
