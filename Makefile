# Anvil — local dev helpers
# Run `make check` before pushing to catch CI failures early.
# Mirrors exactly what .github/workflows/ci.yml runs.

PYTHON  := .venv/bin/python
RUFF    := .venv/bin/ruff
BANDIT  := .venv/bin/bandit
PYTEST  := .venv/bin/python -m pytest

.PHONY: check lint test fmt audit-cargo audit-npm install-hooks

## check: run every CI gate locally (lint + format + bandit + tests + cargo + npm)
check: lint test audit-cargo audit-npm

lint:
	$(RUFF) check backend/ tests/ anvil_mcp/
	$(RUFF) format --check backend/ tests/ anvil_mcp/
	$(BANDIT) -r backend/ -c backend/pyproject.toml -q

test:
	$(PYTEST) tests/ --tb=short -q

## audit-cargo: cargo audit (ignores listed via src-tauri/.cargo/audit.toml)
audit-cargo:
	@if command -v cargo-audit >/dev/null 2>&1; then \
		cd src-tauri && cargo audit; \
	else \
		echo "⚠ cargo-audit not installed — skipping (run: cargo install cargo-audit --locked)"; \
	fi

## audit-npm: npm audit high+ vulnerabilities
audit-npm:
	npm audit --audit-level=high

## fmt: auto-fix formatting
fmt:
	$(RUFF) format backend/ tests/ anvil_mcp/
	$(RUFF) check --fix backend/ tests/ anvil_mcp/

## install-hooks: wire .githooks/pre-push into your local git config
install-hooks:
	git config core.hooksPath .githooks
	@echo "pre-push hook installed — 'make check' will run before every push"
