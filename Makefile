.PHONY: install test lint typecheck audit verify update-deps

PYTHON ?= python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest tests -q
RUFF := ruff check .
FORMAT := ruff format --check .
MYPY := $(PYTHON) -m mypy .
COMPILE := $(PYTHON) -m compileall -q .

install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.lock
	$(PIP) check

test:
	$(PYTHON) -m pytest tests -q

lint:
	ruff check .
	ruff format --check .

typecheck:
	$(MYPY)

audit:
	$(PIP) install "pip-audit>=2.7,<3"
	pip-audit -r requirements.lock

verify: compile test lint typecheck
	@echo "Verification passed"

compile:
	$(COMPILE)

update-deps:
	$(PIP) install --upgrade pip-tools
	pip-compile --no-index --output-file=requirements.lock requirements.txt
