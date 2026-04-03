ARCH := $(shell uname -m)
PREFIX := bin/$(ARCH)

SPHINXTRAIN_SRC := vendor/sphinxtrain
POCKETSPHINX_SRC := vendor/pocketsphinx

SPHINXTRAIN_BUILD := $(SPHINXTRAIN_SRC)/build
POCKETSPHINX_BUILD := $(POCKETSPHINX_SRC)/build

CMU_TOOLKIT_SRC := vendor/cmu_toolkit
CMU_TOOLKIT_BIN := $(CMU_TOOLKIT_SRC)/bin

.PHONY: all pocketsphinx sphinxtrain install clean

all: install

pocketsphinx:
	cmake -S $(POCKETSPHINX_SRC) -B $(POCKETSPHINX_BUILD) \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_C_FLAGS="-w"
	cmake --build $(POCKETSPHINX_BUILD) -j$$(nproc)

sphinxtrain: pocketsphinx
	cmake -S $(SPHINXTRAIN_SRC) -B $(SPHINXTRAIN_BUILD) \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_C_FLAGS="-w"
	cmake --build $(SPHINXTRAIN_BUILD) -j$$(nproc)

cmu_toolkit:
	mkdir -p $(CMU_TOOLKIT_SRC)/bin $(CMU_TOOLKIT_SRC)/lib
	cd $(CMU_TOOLKIT_SRC)/src && make install CFLAGS="-w -O2"

install: sphinxtrain cmu_toolkit
	mkdir -p $(PREFIX)
	find $(SPHINXTRAIN_BUILD) -maxdepth 1 -type f -executable -exec cp {} $(PREFIX)/ \;
	cp $(POCKETSPHINX_BUILD)/pocketsphinx $(PREFIX)/
	cp $(POCKETSPHINX_BUILD)/pocketsphinx_batch $(PREFIX)/
	cp $(POCKETSPHINX_BUILD)/pocketsphinx_lm_convert $(PREFIX)/
	cp $(CMU_TOOLKIT_BIN)/* $(PREFIX)/

link:
	ln -sf $(CURDIR)/sphinx.sh /usr/local/bin/sphinx

unlink:
	rm -f /usr/local/bin/sphinx

clean:
	rm -rf $(SPHINXTRAIN_BUILD) $(POCKETSPHINX_BUILD)
	rm -rf $(PREFIX)
