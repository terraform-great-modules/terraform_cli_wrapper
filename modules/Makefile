# Copyright 2020 Riccardo Scartozzi <me-terraform@risca.eu>
#
# License GPL+3:
#   https://www.gnu.org/licenses/gpl-3.0.html
#
MAKEFILE_VERSION := 0.0.1

.ONESHELL:
.SHELL := /usr/bin/bash
.SHELLFLAGS = -ec  # NB: c is strictly required

CONFIG ?= ./config.json

define Conf
	$(shell jq -r $1 $(CONFIG))
endef


RPATH = $(shell realpath $$(pwd))
CURRENT_FOLDER=$(abspath $(shell pwd))
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
SHSCRIPT := $(CURRENT_FOLDER)/scripts

REPOSITORIES ?= $(call Conf,'.repositories[].name')


help:
	@echo "Welcome to the smart terraform modules wrapper!"
	echo ""
	echo "List of commands:"
	grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo ""
	echo "List of common options:"
	grep -h -E '^[a-zA-Z_-]+.*?#o# .*$$' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = " *?#o# "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: clone-% patch-%
clone-%:
	@bash $(SHSCRIPT)/clone_repo.sh $(CURRENT_FOLDER) '$(call Conf,'.repositories[] | select(.name=="$*")')'

patch-%: clone-%
	@bash $(SHSCRIPT)/apply_repo_patch.sh $(CURRENT_FOLDER) '$(call Conf,'.repositories[] | select(.name=="$*")')'

.PHONY: install-% installall
install-%: clone-% patch-% ;

installall: $(patsubst %,install-%,$(REPOSITORIES))  ## Install and patch locally all of the required modules
	@echo $(REPOSITORIES)
	echo $(patsubst %,install-%,$(REPOSITORIES))

.PHONY: version
version:  ## Get current Makefile version
	@echo $(MAKEFILE_VERSION)
