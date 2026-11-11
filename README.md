# AutomationTestingWithAgentBrowser
## Enterprise Multi-User Automation & Testing Platform
### Strict Company Data Protection — Zero AI / No-LLM Processing

**AutomationTestingWithAgentBrowser** is an enterprise-grade web platform combining visual workflow automation, deterministic testing automation, live browser DOM inspection, real-time WebSocket monitoring, and multi-factor deterministic self-healing using pure `agent-browser` CLI (`0.41.2`).

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
- **Execution & Queue:** Redis 7, Celery 5.4+, Celery Beat (periodic cron scheduling, timezone `Asia/Kolkata`).
- **Browser Engine:** Pure `agent-browser` CLI (`0.41.2`) subprocess adapter with Chromium headless execution.
- **Database:** PostgreSQL 16 (19 enterprise tables with UUID keys, foreign key cascades, and JSONB definitions).
- **Security:** AES-256-GCM Credential Vault, SSRF Network Filtering, JWT RBAC, Immutable Audit Logging.
- **Deployment:** Docker & Docker Compose multi-service orchestration with automated healthchecks.

---

## 🏛 System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEXT.JS ENTERPRISE FRONTEND UI                         │
│  Visual Flow Builder • Live WS Viewport • Object Repository • RBAC Security │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / REST / JWT / WebSocket
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI BACKEND SERVICE                            │
│  /api/v1/flows • /api/v1/tests • /api/v1/credentials • /api/v1/audit • /ws  │
└──────────────┬───────────────────────┬──────────────────────────────┬───────┘
               │                       │                              │
               ▼                       ▼                              ▼
┌─────────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
               POSTGRESQL 16       │  │   REDIS BROKER     │  │ PRIVATE FILE STORAGE   │
│  19 Tables • Neon DB    │  │   Celery Queue     │  │ ./reports/screenshots  │
│  Immutable Versions     │  │   Result Backend   │  │ ./reports/dom_snapshots│
│  AES-256 Credentials    │  │   Event Streaming  │  │ ./reports/artifacts    │
└─────────────────────────┘  └─────────┬──────────┘  └────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CELERY EXECUTION WORKERS                           │
│  Flow DAG Runner  •  Test Assertion Engine  •  Periodic Beat Scheduler      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Subprocess Isolation
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AGENT BROWSER CLI 0.41.2                           │
│     Isolated Sessions  •  DOM Extraction  •  Headless Chromium Execution   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Production via Docker Compose)

Deploy the complete multi-service platform with a single command:

```bash
docker compose up -d --build
```

### Services Launched:
- **`postgres`**: PostgreSQL 16 relational database on port `5432` (healthy status check).
- **`redis`**: Redis 7 message queue & cache on port `6379`.
- **`backend`**: FastAPI REST API & WebSocket server on port `8000` with non-root security.
- **`celery_worker`**: Isolated browser execution daemon running agent-browser CLI.
- **`celery_beat`**: Periodic cron scheduler for automated tests and retention pruning.
- **`frontend`**: Next.js SaaS Web UI on port `3000`.

---

## 💻 Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 20 LTS
- `agent-browser` CLI (`npm install -g agent-browser@0.41.2`)
- PostgreSQL instance running or configured in `.env`
- Redis instance running on port `6379`

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

## 🛡 Zero-AI Policy Compliance Auditor

To run the automated compliance scanner verifying zero AI SDKs, zero LLM endpoints, and strict company data protection:

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

## 🧪 Comprehensive Automated Test Suites

Run the full end-to-end regression test suite:

```bash
python -m pytest tests/test_phase1_stabilization.py \
                 tests/test_phase2_engine.py \
                 tests/test_phase4_monitoring_reporting.py \
                 tests/test_phase5_multiuser_enterprise.py \
                 tests/test_phase6_production_readiness.py \
                 -v
```

### Verified Test Modules (64 Passing Tests):
- **Phase 1: Stabilization & Security (`test_phase1_stabilization.py`)**:
  - `SessionManager` & `AgentBrowserAdapter` dependency injection and session isolation.
  - Flow and test suite execution cancellation lifecycle.
  - Multi-tenant RBAC and project authorization.
  - SSRF protection: loopback and cloud metadata service blocks.
- **Phase 2: Automation Engine Reliability (`test_phase2_engine.py`)**:
  - Native selector validation (`css`, `xpath`, `text`, `role`, `testid`, `ref`).
  - Fallback resolver with deterministic ID, attribute, and testid variants.
  - Dynamic wait engine: `element_visible`, `wait_for_text`, `wait_for_url`, `clickable`.
  - Smart retry policy with exponential backoff and fast-fail security violations.
- **Phase 4: Live Monitoring & Reporting (`test_phase4_monitoring_reporting.py`)**:
  - `ExecutionEventBus` real-time pub/sub buffer and clearing.
  - WebSocket monitor authentication, authorization, and ping/pong.
  - Structured log streaming, level filtering, and text/JSON downloads.
  - Executive HTML report generator with inline SVG donut charts and step waterfalls.
- **Phase 5: Multi-User Platform & Enterprise Features (`test_phase5_multiuser_enterprise.py`)**:
  - Environment management with AES-256 encrypted variables.
  - AES-256-GCM Credential Vault with secret rotation, write-only masking, and domain scoping.
  - Role-based access control with implied permissions (`owner`, `admin`, `developer`, `tester`, `viewer`).
  - Immutable audit logs with JSON/CSV export and automatic retention cleanup.
- **Phase 6: Production Readiness & DevOps (`test_phase6_production_readiness.py`)**:
  - PostgreSQL settings validation and immediate SQLite prohibition.
  - SecretManager AES-256 key derivation and tamper detection.
  - Headless Chromium flag forwarding (`--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`).
  - Celery Beat schedule verification and task registration.

---

## 📄 License & Compliance

All rights reserved. Proprietary enterprise software for internal browser automation and QA testing.
No customer data, source code, or execution logs may be transmitted to external machine learning or AI models under any circumstances.
