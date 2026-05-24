.DEFAULT_GOAL := help

.PHONY: help dev test lint format typecheck clean

help:          ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

dev:           ## Set up dev environment and pre-commit hooks
	uv sync --extra google
	uv run pre-commit install

test:          ## Run tests
	uv run pytest

lint:          ## Lint with ruff
	uv run ruff check polyphon tests

format:        ## Format with ruff
	uv run ruff format polyphon tests

typecheck:     ## Type-check with mypy
	uv run mypy polyphon

clean:         ## Remove generated output files
	rm -rf output/ .mypy_cache/ .pytest_cache/ __pycache__/
