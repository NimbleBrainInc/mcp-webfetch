BUNDLE_NAME = mcp-webfetch
VERSION ?= 0.0.1

.PHONY: help install dev-install format format-check lint lint-fix typecheck test test-cov clean check all bundle run run-http test-http bump

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	uv pip install -e .

dev-install: ## Install with dev dependencies
	uv pip install -e . --group dev

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check code formatting with ruff
	uv run ruff format --check src/ tests/

lint: ## Lint code with ruff
	uv run ruff check src/ tests/

lint-fix: ## Lint and fix code with ruff
	uv run ruff check --fix src/ tests/

typecheck: ## Type check with mypy
	uv run mypy src/

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage
	uv run pytest tests/ -v --cov=src/mcp_webfetch --cov-report=term-missing

clean: ## Clean up artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf bundle/ *.mcpb

run: ## Run the MCP server (stdio)
	uv run python -m mcp_webfetch.server

run-http: ## Run HTTP server with uvicorn
	uv run uvicorn mcp_webfetch.server:app --host 0.0.0.0 --port 8000

test-http: ## Test HTTP server is running
	@echo "Testing health endpoint..."
	@curl -s http://localhost:8000/health | grep -q "healthy" && echo "OK Server is healthy" || echo "FAIL Server not responding"

bundle: ## Build MCPB bundle locally
	@./scripts/build-bundle.sh . $(VERSION)

check: format-check lint typecheck test ## Run all checks

all: clean install format lint typecheck test ## Full workflow

bump: ## Bump version across all files (usage: make bump VERSION=0.2.0)
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump VERSION=x.y.z"; exit 1; fi
	@echo "Bumping version to $(VERSION)..."
	@jq --arg v "$(VERSION)" '.version = $$v' manifest.json > manifest.tmp.json && mv manifest.tmp.json manifest.json
	@jq --arg v "$(VERSION)" '.version = $$v' server.json > server.tmp.json && mv server.tmp.json server.json
	@sed -i '' 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@sed -i '' 's/^__version__ = ".*"/__version__ = "$(VERSION)"/' src/mcp_webfetch/__init__.py
	@echo "Updated:"
	@echo "  manifest.json:                  $$(jq -r .version manifest.json)"
	@echo "  server.json:                    $$(jq -r .version server.json)"
	@echo "  pyproject.toml:                 $$(grep '^version' pyproject.toml)"
	@echo "  src/mcp_webfetch/__init__.py:   $$(grep '__version__' src/mcp_webfetch/__init__.py)"

fmt: format
t: test
l: lint
