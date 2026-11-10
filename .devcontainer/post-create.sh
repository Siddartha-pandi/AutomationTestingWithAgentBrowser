#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Starting Automation Testing Platform Dev Container Setup "
echo "=========================================================="

# 1. Install Python backend dependencies
echo "--> Installing Python requirements..."
pip install --upgrade pip
pip install -r backend/requirements.txt

# 2. Install Node.js frontend dependencies
echo "--> Installing Frontend npm packages..."
cd frontend
npm install
cd ..

# 3. Create required runtime and report directories
echo "--> Ensuring storage directory tree..."
mkdir -p reports/screenshots reports/dom_snapshots reports/artifacts reports/exports reports/sessions

# 4. Wait for PostgreSQL to become ready
echo "--> Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U postgres -d automation_platform_db; do
  echo "    PostgreSQL is not ready yet. Retrying in 2s..."
  sleep 2
done
echo "--> PostgreSQL is ready!"

# 5. Run Alembic Database Migrations
echo "--> Running Alembic database migrations..."
alembic upgrade head

# 6. Seed initial Enterprise tenant & default admin user
echo "--> Seeding enterprise tenant and default roles..."
python scripts/seed_enterprise_tenant.py \
  --admin-email admin@enterprise.local \
  --admin-password AdminPassword123! \
  --org-name "Enterprise QA" || true

echo "=========================================================="
echo " Dev Container Environment Setup Complete!               "
echo "=========================================================="
echo " Default Admin Credentials:                              "
echo "   Email:    admin@enterprise.local                       "
echo "   Password: AdminPassword123!                            "
echo "                                                          "
echo " Commands to launch development services:                "
echo "   - Backend API:    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
echo "   - Celery Worker:  celery -A backend.app.worker.celery_app worker -l INFO"
echo "   - Frontend UI:    cd frontend && npm run dev          "
echo "   - Run Tests:      pytest                               "
echo "=========================================================="

