# Default recipe lists all available commands
default:
    @just --list

# Install Git hooks with prek
install-hooks:
    uv run prek install

alias hooks := install-hooks

# Launch interactive marimo editor for documentation
docs-edit:
    uv run marimo edit docs/docs.py

alias edit-docs := docs-edit

# Export documentation notebook to static HTML
docs-build:
    uv run marimo export html docs/docs.py -o docs/index.html --no-include-code --force

alias build-docs := docs-build

# View examples with marimo
examples:
    uv run marimo edit examples

# Run unit tests with pytest
test:
    uv run pytest

alias tests := test

# Run code linter with ruff
lint:
    uv run ruff check

# Format code with ruff
format:
    uv run ruff format

# Check code format is correct (for CI/CD pipeline)
check-format:
    uv run ruff format --check

# Run linter and tests
check: lint test
