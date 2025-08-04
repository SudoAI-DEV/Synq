# Makefile for Synq development

.PHONY: help install install-dev test test-cov lint format clean build upload check-all

help:
	@echo "Available commands:"
	@echo "  install     - Install package in development mode"
	@echo "  install-dev - Install with development dependencies"
	@echo "  test        - Run tests"
	@echo "  test-cov    - Run tests with coverage"
	@echo "  lint        - Run linting on synq/ and examples/ (ruff + mypy)"
	@echo "  format      - Format code (ruff)"
	@echo "  clean       - Clean build artifacts"
	@echo "  build       - Build package"
	@echo "  upload      - Upload to PyPI"
	@echo "  check-all   - Run all checks (format, lint, test)"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

test-cov:
	pytest --cov=synq --cov-report=html --cov-report=term

lint:
	-ruff check synq/ examples/
	-mypy synq/

format:
	ruff format synq/ tests/ examples/
	-ruff check --fix synq/ examples/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

check-all: format lint test-cov
	@echo "All checks passed!"

# Development shortcuts
dev-setup: install-dev
	pre-commit install

example:
	cd examples && python basic_usage.py