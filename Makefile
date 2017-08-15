# Makefile to help automate tasks
WD := $(shell pwd)
PLATFORM=$(shell uname -s)
PY := .venv/bin/python
SYSPY := $(shell which python3)
PIP := .venv/bin/pip
PEP8 := .venv/bin/pep8
PYTEST := .venv/bin/py.test
FLAKE8 := .venv/bin/flake8


# #######
# INSTALL
# #######
.PHONY: all
all: sysdeps .venv

.PHONY: clean-all
clean-all: clean_venv
	if [ -d dist ]; then \
		rm -r dist; \
    fi


sysdeps:
	sudo apt-get install python3-dev python3-virtualenv


.venv: .venv/bin/python
.venv/bin/python:
	# needs python3-dev to build keystoneclient deps
	python3 -m virtualenv -p $(SYSPY) .venv
	$(PIP) install click
	$(PIP) install python-swiftclient
	$(PIP) install python-keystoneclient
	$(PIP) install jujubundlelib
	$(PIP) install PyMySQL

.PHONY: clean_venv
clean_venv:
	rm -rf .venv


.venv/bin/flake8: .venv
	$(PIP) install flake8

lint: .venv/bin/flake8
	$(FLAKE8) long-running


##
## Long running setup
##

.PHONY: get-logs
get-logs: .venv logs/api/1 logs/api/2
	ifndef NOVA_USERNAME
		$(error NOVA_USERNAME is undefined, source your swift cred file.)
	endif
	swift list production-juju-ps45-cdo-jujucharms-machine-1.canonical.com | grep  201 | grep api.jujucharms.com.log > logs/api/logs1.list
	swift list production-juju-ps45-cdo-jujucharms-machine-2.canonical.com | grep 201 | grep api.jujucharms.com.log > logs/api/logs2.list
	echo "Downloading log files using get.sh"
	cd logs/api && ./get.sh

logs/api/1:
	mkdir -p logs/api/1
logs/api/2:
	mkdir -p logs/api/2


.PHONY: _initdb
_initdb: .venv

	$(PY) long-running/longrunning.py initdb

.PHONY: updatedb
updatedb: .venv
	$(PY) long-running/longrunning.py updatedb

.PHONY: longrunning
longrunning: .venv
	$(PY) long-running/longrunning.py run summary
	$(PY) long-running/longrunning.py run latest-summary
	$(PY) long-running/longrunning.py run model-ages
	$(PY) long-running/longrunning.py run models-per-day
	$(PY) long-running/longrunning.py run latest-versions
	$(PY) long-running/longrunning.py run latest-clouds
	$(PY) long-running/longrunning.py run latest-clouds-regions
