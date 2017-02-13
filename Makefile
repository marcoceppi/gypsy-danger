# Makefile to help automate tasks
WD := $(shell pwd)
PY := bin/python
PIP := bin/pip
PEP8 := bin/pep8
PYTEST := bin/py.test


# #######
# INSTALL
# #######
.PHONY: all
all: sysdeps venv

.PHONY: clean-all
clean-all: clean_venv
	if [ -d dist ]; then \
		rm -r dist; \
    fi


sysdeps:
	sudo apt-get install python3-dev


venv: bin/python
bin/python:
	# needs python3-dev to build keystoneclient deps
	virtualenv -p /usr/bin/python3 .
	bin/pip install click
	bin/pip install python-swiftclient
	bin/pip install python-keystoneclient

.PHONY: clean_venv
clean_venv:
	rm -rf bin include lib local man share


bin/flake8: venv
	bin/pip install flake8

lint: bin/flake8
	flake8 long-running


###
# Long running setup
###
check-swift:
ifndef NOVA_USERNAME
    $(error NOVA_USERNAME is undefined, source your swift cred file.)
endif

.PHONY: get-logs
get-logs: logs/api/1 logs/api/2 check-swift
	swift list production-juju-ps45-cdo-jujucharms-machine-1.canonical.com | grep  201 | grep api.jujucharms.com.log > logs/api/logs1.list
	swift list production-juju-ps45-cdo-jujucharms-machine-2.canonical.com | grep 201 | grep api.jujucharms.com.log > logs/api/logs2.list
	echo "Downloading log files using get.sh"
	cd logs/api && ./get.sh

logs/api/1:
	mkdir -p logs/api/1
logs/api/2:
	mkdir -p logs/api/2


.PHONY: _initdb
_initdb:
	$(PY) long-running/longrunning.py initdb

.PHONY: longrunning
longrunning:
	$(PY) long-running/longrunning.py run summary
	$(PY) long-running/longrunning.py run latest-summary
	$(PY) long-running/longrunning.py run model-ages
	$(PY) long-running/longrunning.py run models-per-day
	$(PY) long-running/longrunning.py run latest-versions
	$(PY) long-running/longrunning.py run latest-clouds
	$(PY) long-running/longrunning.py run latest-clouds-regions
