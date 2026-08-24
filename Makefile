.PHONY: install test lint typecheck frontend-check benchmark audit run-backend run-frontend

install:
	python3 -m venv .venv
	.venv/bin/pip install -e 'backend[dev]'
	cd frontend && npm ci

test:
	.venv/bin/pytest backend/tests

lint:
	.venv/bin/ruff check backend/limitx backend/tests
	cd frontend && npm run lint

typecheck:
	.venv/bin/mypy backend/limitx
	cd frontend && npm run typecheck

frontend-check:
	cd frontend && npm run lint && npm run typecheck && npm run build

benchmark:
	.venv/bin/python -m limitx.bench --scenario mixed --orders 100000 --seed 42 --runs 3

audit:
	.venv/bin/python -m limitx.audit data/session.jsonl

run-backend:
	.venv/bin/uvicorn limitx.api.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

