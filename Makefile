.PHONY: test lint integration all help setup hooks

# Resolved from the environment so the suite runs on any machine. Override to
# target a specific interpreter, e.g.  make test PYTHON=~/venv/bin/python
PYTHON ?= $(shell command -v python3 2>/dev/null || command -v python)
PYTEST ?= $(PYTHON) -m pytest
RUFF   ?= $(PYTHON) -m ruff

help:
	@echo "pyinfra-framework test suite"
	@echo ""
	@echo "make setup       - Install pytest and ruff into the active environment"
	@echo "make hooks       - Install git hooks (privacy scan before every commit)"
	@echo "make test       - Run unit tests (no SSH)"
	@echo "make lint       - Run ruff linting"
	@echo "make integration - Run integration tests (requires SSH to controller.paris)"
	@echo "make all        - Run all tests: lint + unit + integration"
	@echo ""

hooks:
	sh scripts/install-hooks.sh

setup:
	$(PYTHON) -m pip install pytest ruff pyinfra

test:
	$(PYTEST) tests/ -v -m "not integration"

lint:
	$(RUFF) check .

integration:
	$(PYTEST) tests/ -v -m integration

all: lint test integration

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage
