# Avvia Intelligence Admin Makefile
# Convenience commands for development

.PHONY: help install server reflex clean test lint format check alembic migrate migrate-auto migrate-history migrate-down setup-azure-providers docker-build docker-tag docker-push docker-login build build-container-app docker-verify docker-config load-env

# Default target
help:
	@echo "Available targets:"
	@echo "  instlal      - Install dependencies using uv"
	@echo "  clean        - Clean cache and build artifacts"
	@echo "  test         - Run tests"
	@echo "  lint         - Run linting with ruff"
	@echo "  format       - Format code with ruff"
	@echo "  check        - Run linting and formatting checks"
	@echo ""

# Install dependencies
install:
	uv sync

# Clean cache and build artifacts
clean:
	rm -rf __pycache__/
	rm -rf .cache/
	rm -rf .states/
	rm -rf .web/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Run tests
test:
	uv run pytest

# Run linting
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .
	uv run ruff check --fix .

# Check linting and formatting
check:
	uv run ruff check .
	uv run ruff format --check .
