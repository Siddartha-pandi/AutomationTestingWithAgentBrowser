# Enterprise Automation & Testing Platform - Backend Core

High-performance asynchronous REST API backend powered by FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 16, and Celery 5.4+.

Strictly **Zero-AI / NO_DATA Company Data Protection Architecture**.

---

## 1. Quick Start

Run from the repository root:

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Apply database migrations
alembic upgrade head

# 3. Launch FastAPI server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2. Environment Configuration

The backend automatically loads configurations from the repository-root `.env` file:

```bash
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/automation_platform_db
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
JWT_SECRET=your-64-char-secure-secret
```

---

## 3. Architecture & Standards

- **Database:** Strictly PostgreSQL 16 with `psycopg3` binary driver. SQLite is prohibited.
- **Browser Automation:** Solely executes `agent-browser` CLI (`0.41.2`) subprocess isolation.
- **Background Jobs:** Celery workers dispatch asynchronous test suites and scheduled DAG flows.
- **Interactive Documentation:** Swagger UI at `http://localhost:8000/docs` and ReDoc at `http://localhost:8000/redoc`.
