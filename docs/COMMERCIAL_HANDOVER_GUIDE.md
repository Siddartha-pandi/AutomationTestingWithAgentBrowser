# Commercial Handover & Enterprise Operations Manual
## Turnkey Enterprise Delivery for Software Acquisition
### Platform: AgentFlow Browser Flow & Testing Automation Platform

---

> **Document Classification:** Confidential — Enterprise Commercial Handover  
> **Target Audience:** Client CTO, VP of Engineering, Lead Software Architect, DevOps & Security Reviewers  
> **Compliance Standard:** 100% Zero-AI Company Data Protection Guarantee (NO_DATA Policy)  
> **Browser Engine:** Pure `agent-browser` CLI (`v0.41.2`) Subprocess Adapter  
> **Database:** PostgreSQL 16 (Relational Schema + Alembic Migrations)  
> **Distributed Workers:** Redis 7 + Celery 5.4+  

---

## 1. Executive Summary & Core Intellectual Property (IP)

This platform is a commercial-grade, multi-tenant visual browser flow automation, testing automation, and browser intelligence software suite. It combines visual flow authoring (inspired by Automa), enterprise test management (inspired by WrightTest), and asynchronous workflow orchestration (inspired by n8n).

### Key Proprietary Assets Included:
1. **Deterministic Element Recognition & Self-Healing Engine:**
   - Multi-factor mathematical scoring evaluating stable attributes ($35\%$), ARIA accessible roles and names ($25\%$), DOM hierarchy Jaccard overlap ($20\%$), geometric flow ($15\%$), and normalized Levenshtein string distance ($5\%$).
   - Autonomous Tier-1 repair ($\ge 95\%$) and Tier-2 human-in-the-loop governance ($85\% - 94\%$).
   - **Zero AI / Zero LLM reliance:** Predictable, deterministic, zero-hallucination execution.
2. **Isolated Subprocess Browser Adapter:**
   - Exclusively uses `agent-browser` CLI (`0.41.2`) subprocess sessions (`--session <uuid>`), bypassing brittle WebDriver binaries and avoiding external browser automation engines.
3. **Visual DAG Canvas & Categorized Action Catalog:**
   - 30+ deterministic browser, logic, data operation, and governance nodes with live execution highlighting.
4. **Enterprise Multi-Tenancy & RBAC:**
   - Multi-tenant workspace isolation (`projects`, `project_members`, `environments`, `credentials`).
   - 5-tier role hierarchy: `owner`, `admin`, `lead_qa`, `developer`, `viewer`.

---

## 2. Mandatory Zero-AI Compliance Guarantee

The purchasing enterprise receives an enforceable, audit-verified guarantee:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                 ZERO-AI & COMPANY DATA PROTECTION CERTIFICATE               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. ZERO Third-Party AI Services (OpenAI, Anthropic, Gemini, Claude, etc.)   │
│ 2. ZERO Local Language Models (Ollama, vLLM, LM Studio, HuggingFace)       │
│ 3. ZERO Vector Database Embeddings or Probabilistic Guessing               │
│ 4. ZERO Data Telemetry, DOM snapshot, or Credential Exfiltration            │
│ 5. 100% Pure Deterministic Algorithms & Mathematical Graph Topology        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Automated Handover Acceptance Audit:**
```bash
python scripts/verify_zero_ai_policy.py
```

---

## 3. Turnkey Production Deployment (Docker Compose)

The entire enterprise platform can be launched in a multi-container isolated stack using Docker Compose.

### Step 1: Environment Configuration
Copy the production environment template:
```bash
cp .env.example .env
```
Generate secure keys:
```bash
# 1. Generate JWT Secret Key (64 chars)
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"

# 2. Generate AES-256 Vault Master Key (32 bytes hex)
python -c "import secrets; print('CREDENTIALS_MASTER_KEY=' + secrets.token_hex(32))"
```
Paste the generated secrets into your `.env` file.

### Step 2: Launch Platform Services
```bash
docker compose up -d --build
```

### Services Initialized:
| Container | Service | Port | Description |
| :--- | :--- | :--- | :--- |
| `automation_testing_postgres` | PostgreSQL 16 | `5432` | Relational database (19 schema tables) |
| `automation_testing_redis` | Redis 7 | `6379` | Celery broker & real-time state |
| `automation_testing_api` | FastAPI Backend | `8000` | REST API core & OpenAPI documentation |
| `automation_testing_worker` | Celery Worker | — | Headless `agent-browser` execution pool |
| `automation_testing_beat` | Celery Beat | — | Cron task scheduler (`Asia/Kolkata`) |
| `automation_testing_frontend` | Next.js 16 SaaS | `3000` | Enterprise React 19 UI & DAG Canvas |

---

## 4. First-Boot Enterprise Tenant Seeding

After deploying the database, initialize your enterprise organization, roles, administrator account, and canonical test suites:

```bash
python scripts/seed_enterprise_tenant.py \
  --admin-email admin@yourcompany.com \
  --admin-password "YourSecureP@ssw0rd!" \
  --org-name "Your Enterprise Org" \
  --env-name "Production" \
  --base-url "https://app.yourcompany.com"
```

### Default Provisioned Access:
- **Web UI Portal:** `http://localhost:3000`
- **Super Admin Login:** `admin@yourcompany.com`
- **Initial Password:** Configured during command invocation
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Interactive ReDoc:** `http://localhost:8000/redoc`

---

## 5. White-Labeling & Custom Branding Configuration

The platform supports full white-labeling. Update your `.env` or container environment variables without modifying source code:

```bash
# Displayed in UI Header, Navigation Sidebar & Browser Tab Title
NEXT_PUBLIC_APP_NAME="YourCompany Automation Hub"

# Sub-branding or parent organization title
NEXT_PUBLIC_COMPANY_NAME="YourCompany QA Engineering"

# Technical support & inquiry link
NEXT_PUBLIC_SUPPORT_EMAIL="qa-support@yourcompany.com"
```

Rebuild the frontend container to apply the new branding:
```bash
docker compose build frontend && docker compose up -d frontend
```

---

## 6. Pre-Flight Acceptance Audit (Handover Verification)

Before signing off on platform handover, the client's DevOps / Engineering lead can execute the automated 10-point production audit:

```bash
python scripts/production_readiness_check.py
```

### Verified Checks:
1. `[PASS]` Mandatory Zero-AI Policy (NO_DATA Protection)
2. `[PASS]` Sole Browser Engine Integrity (`agent-browser v0.41.2`)
3. `[PASS]` Relational Database Stack (PostgreSQL 16 + Alembic)
4. `[PASS]` Distributed Worker Queue (Redis 7 + Celery 5.4+)
5. `[PASS]` Cryptographic Security Vault (AES-256-GCM + JWT)
6. `[PASS]` Private File Storage Infrastructure (`chmod 0600`)
7. `[PASS]` Multi-User RBAC & Organization Tenancy
8. `[PASS]` Frontend Enterprise SaaS Bundle (Next.js 16 + React Flow)
9. `[PASS]` Turnkey Containerization & Orchestration (`docker-compose.yml`)
10. `[PASS]` Commercial Handover Tooling & Documentation

---

## 7. Security Hardening & Secret Management

1. **AES-256-GCM Credential Vault:**
   - Plaintext passwords and API tokens entered in the Credentials module are encrypted with authenticated AES-256-GCM before database insertion.
   - Credentials are decrypted in-memory only during Celery worker step dispatch and are strictly scrubbed by the log redactor.
2. **Master Key Rotation:**
   - To rotate the `CREDENTIALS_MASTER_KEY`, update the master key in the secure vault orchestrator, trigger the re-encryption utility, and restart workers.
3. **SSRF Domain Whitelisting:**
   - Each Environment specifies `allowed_domains` (e.g. `["*.yourcompany.com"]`). Browser navigations attempting unauthorized external hostnames are aborted immediately.

---

## 8. Backup, Restore & Disaster Recovery (DR)

### Database Backup (PostgreSQL):
```bash
docker exec -t automation_testing_postgres pg_dump -U postgres automation_platform_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Database Restore:
```bash
gunzip < backup_20261110_000000.sql.gz | docker exec -i automation_testing_postgres psql -U postgres automation_platform_db
```

### Artifacts & Screenshots Backup:
```bash
tar -czvf reports_backup_$(date +%Y%m%d).tar.gz ./reports
```

---

## 9. Hardware & Sizing Recommendations

| Deployment Tier | Concurrent Browser Workers | CPU | RAM | Storage | Target Scale |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Starter / PoC** | 2 Workers | 2 Cores | 4 GB | 20 GB SSD | Up to 500 test executions / day |
| **Standard Enterprise** | 4–8 Workers | 4–8 Cores | 16 GB | 100 GB NVMe | Up to 5,000 test executions / day |
| **High-Throughput** | 16+ Workers | 16+ Cores | 32–64 GB | 500 GB NVMe | 25,000+ test executions / day |

---

## 10. Technical Support & Sign-Off

The platform has been audited, verified with clean test suites (54 passed unit & integration tests), zero TypeScript compilation errors, and complete architectural documentation.
