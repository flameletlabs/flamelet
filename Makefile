.PHONY: test lint integration all help setup

PYTHON := /home/syseng/.local/share/pipx/venvs/pyinfra/bin/python3
PYTEST := /home/syseng/.local/share/pipx/venvs/pyinfra/bin/pytest
RUFF   := /home/syseng/.local/share/pipx/venvs/pyinfra/bin/ruff

help:
	@echo "pyinfra-framework test suite"
	@echo ""
	@echo "make setup       - Install pytest and ruff into pyinfra venv (one-time)"
	@echo "make test       - Run unit tests (no SSH)"
	@echo "make lint       - Run ruff linting"
	@echo "make integration - Run integration tests (requires SSH to controller.work)"
	@echo "make all        - Run all tests: lint + unit + integration"
	@echo ""

setup:
	pipx inject pyinfra pytest ruff

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
