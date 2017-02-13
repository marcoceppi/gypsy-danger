# Makefile to help automate tasks
WD := $(shell pwd)
PY := bin/python
PIP := bin/pip
PEP8 := bin/pep8
PYTEST := bin/py.test

# ###########
# Tests rule!
# ###########
# .PHONY: test
# test: venv develop $(PYTEST)
# 	$(PYTEST) -q --tb native -s tests
#
# .PHONY: test-coverage
# test-coverage: venv develop $(PYTEST)
# 	$(PYTEST) -q --cov breadability tests
#
# $(PYTEST):
# 	$(PIP) install -r requirements.txt

# #######
# INSTALL
# #######
.PHONY: all
all: venv deps develop

.PHONY: clean-all
clean-all: clean_venv
	if [ -d dist ]; then \
		rm -r dist; \
    fi


venv: bin/python
bin/python:
	virtualenv -p /usr/bin/python3 .
	bin/pip install click

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
.PHONY: get-logs
get-logs: logs/api/1 logs/api/2
	swift list production-juju-ps45-cdo-jujucharms-machine-1.canonical.com G 201610 G api.jujucharms.com.log > logs/api/logs1.list
	swift list production-juju-ps45-cdo-jujucharms-machine-2.canonical.com G 201610 G api.jujucharms.com.log > logs/api/logs2.list
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


# .PHONY: deps
# deps: venv
# 	$(PIP) install -r requirements.txt


# .PHONY: develop
# develop: lib/python*/site-packages/breadability.egg-link
# lib/python*/site-packages/breadability.egg-link:
# 	$(PY) setup.py develop


# # ###########
# # Deploy
# # ###########
# .PHONY: dist
# dist:
# 	$(PY) setup.py sdist
#
# .PHONY: upload
# upload:
# 	$(PY) setup.py sdist upload
#
# .PHONY: version_update
# version_update:
# 	$(EDITOR) setup.py CHANGELOG.rst
