# Anvil — local dev helpers
# Run `make check` before pushing to catch CI failures early.

PYTHON  := .venv/bin/python
RUFF    := .venv/bin/ruff
BANDIT  := .venv/bin/bandit
PYTEST  := .venv/bin/python -m pytest

.PHONY: check lint test fmt install-hooks

## check: run every CI gate locally (lint + format + bandit + tests)
check: lint test

lint:
	$(RUFF) check backend/ tests/ anvil_mcp/
	$(RUFF) format --check backend/ tests/ anvil_mcp/
	$(BANDIT) -r backend/ -c backend/pyproject.toml -q

test:
	$(PYTEST) tests/ --tb=short -q

## fmt: auto-fix formatting
fmt:
	$(RUFF) format backend/ tests/ anvil_mcp/
	$(RUFF) check --fix backend/ tests/ anvil_mcp/

## install-hooks: wire .githooks/pre-push into your local git config
install-hooks:
	git config core.hooksPath .githooks
	@echo "pre-push hook installed — 'make check' will run before every push"
