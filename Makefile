.PHONY: help install install-backend install-frontend install-automation backend frontend automation build test test-unit test-integration test-automation clean audit

help:
	@echo "Available commands:"
	@echo "  make install           Install all dependencies (backend, frontend, automation-service)"
	@echo "  make install-backend   Install Python backend dependencies"
	@echo "  make install-frontend  Install Next.js frontend dependencies"
	@echo "  make install-automation Install NestJS Playwright automation service dependencies"
	@echo "  make backend           Start the FastAPI backend server (port 8000)"
	@echo "  make frontend          Start the Next.js frontend dev server (port 3000)"
	@echo "  make automation        Start the NestJS Playwright automation engine (port 3001)"
	@echo "  make build             Build the frontend for production"
	@echo "  make test              Run all pytest test suites"
	@echo "  make test-unit         Run backend unit tests"
	@echo "  make test-integration  Run backend integration tests"
	@echo "  make test-automation   Run NestJS Playwright test suites"
	@echo "  make audit             Run Zero-AI compliance and production readiness audits"
	@echo "  make clean             Remove temporary artifacts, test outputs, and caches"

install: install-backend install-frontend install-automation

install-backend:
	python -m pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

install-automation:
	cd automation-service && npm install

backend:
	python -m backend

frontend:
	cd frontend && npm run dev

automation:
	cd automation-service && npm run start:dev

build:
	cd frontend && npm run build

test:
	python -m pytest tests -v

test-unit:
	python -m pytest tests/unit -v

test-integration:
	python -m pytest tests/integration -v

test-automation:
	cd automation-service && npm test

audit:
	python scripts/verify_zero_ai_policy.py
	python scripts/production_readiness_check.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').rglob('.pytest_cache')]"
