# Pipeline Doctor Makefile
# Development and build automation

.PHONY: help install test lint format typecheck build clean docs release docker-build docker-push

# Default target
help:
	@echo "Pipeline Doctor - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install          Install package in development mode"
	@echo "  install-dev      Install with development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-cov         Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linter (ruff)"
	@echo "  format           Format code (ruff)"
	@echo "  typecheck        Run type checker (mypy)"
	@echo "  check            Run all quality checks"
	@echo ""
	@echo "Building:"
	@echo "  build            Build distribution packages"
	@echo "  clean            Clean build artifacts"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Build documentation"
	@echo "  docs-serve       Serve documentation locally"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-push      Push Docker image"
	@echo "  docker-run       Run Docker container"
	@echo ""
	@echo "Release:"
	@echo "  release          Create a new release"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Testing
test:
	pytest

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v -m integration

test-cov:
	pytest --cov=pipeline_doctor --cov-report=html --cov-report=term-missing

# Code Quality
lint:
	ruff check src tests

format:
	ruff format src tests

typecheck:
	mypy src

check: lint format typecheck
	@echo "All checks passed!"

# Building
build: clean
	python -m build

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Documentation
docs:
	mkdocs build

docs-serve:
	mkdocs serve

# Docker
docker-build:
	docker build -t pipeline-doctor:latest .

docker-push:
	docker tag pipeline-doctor:latest ghcr.io/your-org/pipeline-doctor:latest
	docker push ghcr.io/your-org/pipeline-doctor:latest

docker-run:
	docker run --rm -it \
		-e GITHUB_TOKEN \
		-e GITLAB_TOKEN \
		-e JENKINS_URL \
		-e JENKINS_USER \
		-e JENKINS_TOKEN \
		-e AZURE_ORG \
		-e AZURE_PROJECT \
		-e AZURE_PAT \
		-e CIRCLECI_TOKEN \
		-e CIRCLECI_PROJECT \
		-v $(PWD)/reports:/app/reports \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/config:/app/config \
		pipeline-doctor:latest --help

# Release
release:
	@echo "Creating release..."
	@read -p "Version: " version; \
	git tag -a v$$version -m "Release v$$version"; \
	git push origin v$$version

# Development helpers
run-analyze:
	pipeline-doctor analyze --platform github --repo $(GITHUB_OWNER)/$(GITHUB_REPO) --pipeline $(PIPELINE_ID)

run-monitor:
	pipeline-doctor monitor --platform github --repo $(GITHUB_OWNER)/$(GITHUB_REPO) --pipeline $(PIPELINE_ID)

run-report:
	pipeline-doctor report --platform github --repo $(GITHUB_OWNER)/$(GITHUB_REPO) --pipeline $(PIPELINE_ID) --days 30

run-scan:
	pipeline-doctor scan config/example.yaml --platform github --format markdown

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Dependency management
deps-update:
	pip install --upgrade pip
	pip install -e ".[dev]" --upgrade

deps-check:
	pip list --outdated

# Security
security-scan:
	bandit -r src -f json -o bandit-report.json

# Profiling
profile:
	python -m cProfile -o profile.stats -m pipeline_doctor.cli.main analyze --help
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"