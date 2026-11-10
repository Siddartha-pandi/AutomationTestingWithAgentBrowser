# AutomationTestingWithAgentBrowser
## Enterprise Multi-User Automation & Testing Platform
### Strict Company Data Protection — Zero AI / No-LLM Processing

**AutomationTestingWithAgentBrowser** is an enterprise-grade web platform combining visual workflow automation, deterministic testing automation, live browser DOM inspection, and multi-factor deterministic self-healing using pure `agent-browser` CLI (`0.41.2`).

---

## 🔒 Mandatory Company Data Protection Guarantee

Company data must **NEVER** be shared with AI services. This application is architected and executed **strictly without AI**:

- ❌ **Zero AI APIs:** No OpenAI, ChatGPT, Claude, Anthropic, Gemini, or Cohere APIs.
- ❌ **Zero Local Inference:** No Ollama, vLLM, HuggingFace, or local model execution.
- ❌ **Zero AI-Generated Locators or Flows:** 100% deterministic mathematical algorithms (Levenshtein edit-distance, Jaccard ancestor sets, ARIA semantics, attribute stability).
- ❌ **Zero Outbound Telemetry:** DOM snapshots, screenshots, and logs remain in private approved storage with automatic secret redaction.
- ✅ **Deterministic Self-Healing:** Rule-based heuristics with multi-factor scoring (95% auto-heal tier, 85–94% human-in-the-loop approval gate, ≥98% destructive safety check).

---

## 🛠 Technology Stack

- **Frontend:** Next.js 16 (App Router), TypeScript, Tailwind CSS, `@xyflow/react` (React Flow), Recharts, Lucide Icons.
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (PostgreSQL only via `psycopg` 3), Alembic.
- **Execution & Queue:** Redis 7, Celery 5.7, Celery Beat (periodic cron scheduling, timezone `Asia/Kolkata`).
- **Browser Engine:** Pure `agent-browser` CLI (`0.41.2`) subprocess adapter.
- **Database:** PostgreSQL (19 enterprise tables with UUID keys, foreign key cascades, and JSONB definitions).
- **Deployment:** Docker Compose multi-service orchestration.

---

## 🏛 System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEXT.JS ENTERPRISE FRONTEND UI                         │
│  Visual Flow Builder  •  Visual Test Builder  •  Live DOM Explorer  •  RBAC │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST / JWT
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND SERVICE                            │
│  /api/v1/flows • /api/v1/tests • /api/v1/healing • /api/v1/artifacts        │
└──────────────┬───────────────────────┬──────────────────────────────┬───────┘
               │                       │                              │
               ▼                       ▼                              ▼
┌─────────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
│     POSTGRESQL 16       │  │   REDIS BROKER     │  │ PRIVATE FILE STORAGE   │
│  19 Tables • Neon DB    │  │   Celery Queue     │  │ ./reports/screenshots  │
│  Immutable Versions     │  │   Result Backend   │  │ ./reports/dom_snapshots│
└─────────────────────────┘  └─────────┬──────────┘  │ ./reports/artifacts    │
                                       │             └────────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CELERY EXECUTION WORKERS                           │
│  Flow DAG Runner  •  Test Assertion Engine  •  Periodic Beat Scheduler      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Subprocess Isolation
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT BROWSER CLI 0.41.2                           │
│     Isolated Sessions  •  DOM Extraction  •  Headless Browser Execution     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- Node.js 20 LTS
- `agent-browser` CLI installed (`npm install -g agent-browser@0.41.2`)
- PostgreSQL instance running or configured in `.env`

### 2. Backend Setup
```bash
# Install backend dependencies
python -m pip install -r backend/requirements.txt

# Launch FastAPI development server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at: `http://127.0.0.1:8000/docs`

### 3. Background Workers (Celery & Redis)
```bash
# Start Celery execution worker
celery -A backend.app.worker.celery_app worker -l INFO -c 4

# Start Celery Beat periodic scheduler
celery -A backend.app.worker.celery_app beat -l INFO
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Dashboard available at: `http://localhost:3000`

---

## 🐳 Production Deployment (Docker Compose)

Deploy the complete multi-service stack with a single command:

```bash
docker compose up -d --build
```

Services launched:
- `postgres`: PostgreSQL 16 relational database on port `5432`
- `redis`: Redis 7 message queue on port `6379`
- `backend`: FastAPI API server on port `8000`
- `celery_worker`: Background browser execution daemon
- `celery_beat`: Periodic cron scheduler
- `frontend`: Next.js web application on port `3000`

---

## 💻 Instant Team Onboarding (VS Code Dev Container)

For teammates wanting a zero-config local development setup:
1. Open the repository in VS Code or Cursor with Docker Desktop running.
2. When prompted, click **"Reopen in Container"** (or press `F1` -> `Dev Containers: Reopen in Container`).
3. The Dev Container automatically provisions Python 3.11, Node.js 20, the `agent-browser` engine, PostgreSQL 16, Redis 7, installs all dependencies, runs Alembic migrations, and seeds test data.
4. See [.devcontainer/README.md](.devcontainer/README.md) for full usage instructions.

---

To run the automated compliance scanner verifying zero AI SDKs, zero LLM endpoints, and strict data protection:

```bash
python scripts/verify_zero_ai_policy.py
```

Expected output:
```text
======================================================================
AUTOMATION TESTING WITH AGENT BROWSER
Zero-AI & Company Data Protection Policy Audit
======================================================================
[+] Audit 1: 0 Prohibited AI SDKs installed in Python environment (PASS)
[+] Audit 2: 0 External AI API endpoints referenced in codebase (PASS)
[+] Audit 3: 0 AI/LLM SDK imports in backend/frontend source code (PASS)
[+] Audit 4: 0 Prohibited AI routes in FastAPI application (PASS)
[+] Audit 5: Pure deterministic rule-based matching engine verified (PASS)

Policy Status: 100% VERIFIED COMPLIANT (Zero AI / Strict Data Protection)
======================================================================
```

---

## 🧪 Comprehensive Test Suite

Run the complete 75-test platform regression suite:

```bash
python -m pytest tests/ -v
```

Verified test modules:
- `tests/test_agent_browser_adapter.py`: Pure agent-browser CLI subprocess execution.
- `tests/test_database_postgres.py`: PostgreSQL 19-table schema and SQLite rejection.
- `tests/test_auth_rbac.py`: Multi-user JWT, bcrypt hashing, and RBAC permissions.
- `tests/test_dom_extraction.py`: DOM extraction and multi-factor element profiles.
- `tests/test_self_healing.py`: Deterministic scoring engine and human approval tiers.
- `tests/test_flow_engine.py`: React Flow DAG traversal, variables, and circuit breakers.
- `tests/test_testing_engine.py`: 13 deterministic assertions and legacy test migrations.
- `tests/test_worker_tasks.py`: Celery worker tasks, eager runners, and Beat schedules.
- `tests/test_artifacts_reports.py`: SHA-256 digests, tamper detection, and HTML exports.
- `tests/test_security_audit_policy.py`: Automated zero-AI and SSRF policy verification.

---

## 📖 Complete Platform User Manual

For an in-depth operational walkthrough, architectural diagrams, mathematical self-healing formulas, and full UI screenshots:
- **Markdown Manual:** [docs/USER_MANUAL.md](docs/USER_MANUAL.md)
- **Interactive HTML Manual:** [docs/USER_MANUAL.html](docs/USER_MANUAL.html)
- **Visual Diagram Assets:** [docs/images/](docs/images/)

---

## 📄 License & Compliance

All rights reserved. Proprietary enterprise software for internal test automation.
No customer data, source code, or execution logs may be transmitted to external machine learning or AI models under any circumstances.
