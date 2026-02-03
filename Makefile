SHELL := /bin/bash

.PHONY: migrate-json-check migrate-json-fix

migrate-json-check:
	@[ -f .env ] || (echo "Missing .env"; exit 1)
	@[ -x .venv/bin/python ] || (echo "Missing .venv/bin/python"; exit 1)
	@set -a; source .env; set +a; .venv/bin/python scripts/fix_postgres_json.py --dry-run

migrate-json-fix:
	@[ -f .env ] || (echo "Missing .env"; exit 1)
	@[ -x .venv/bin/python ] || (echo "Missing .venv/bin/python"; exit 1)
	@set -a; source .env; set +a; .venv/bin/python scripts/fix_postgres_json.py
