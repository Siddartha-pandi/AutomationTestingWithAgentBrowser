.PHONY: help install install-backend install-frontend backend frontend build

help:
	@echo "Available commands:"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make install-backend Install Python backend dependencies"
	@echo "  make install-frontend Install frontend dependencies"
	@echo "  make backend         Start the FastAPI backend"
	@echo "  make frontend        Start the Next.js frontend"
	@echo "  make build           Build the frontend for production"

install: install-backend install-frontend

install-backend:
	python -m pip install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

backend:
	python -m backend

frontend:
	cd frontend && npm run dev

build:
	cd frontend && npm run build
