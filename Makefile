# Makefile for easy development workflows.
# See docs/development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := default

.PHONY: default install lint lint-check test upgrade build clean docs docs-serve

default: install lint test

install:
	uv sync --all-extras

lint:
	uv run python devtools/lint.py

# Check-only lint, matching CI (does not modify files).
lint-check:
	uv run python devtools/lint.py --check

test:
	uv run pytest

upgrade:
	uv sync --upgrade --all-extras --dev

build:
	uv build

# Build the docs site (strict mode, matching CI).
docs:
	uv run --group docs mkdocs build --strict

# Serve the docs locally with live reload at http://127.0.0.1:8000
docs-serve:
	uv run --group docs mkdocs serve

clean:
	-rm -rf dist/
	-rm -rf *.egg-info/
	-rm -rf .pytest_cache/
	-rm -rf .mypy_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
