# Known Issues, Technical Debt & Mitigation Matrix

**Document Version:** 3.1.0  
**Project:** AutomationTestingWithAgentBrowser  
**Date:** November 13, 2026  
**Status:** Monitored Operational Risk Log  

---

## 1. Technical Debt & Operational Observations

| Issue ID | Subsystem | Description & Impact | Current Behavior | Mitigation & Resolution |
|---|---|---|---|---|
| **ISS-001** | Database / Testing | 32 Pytest integration tests skip when PostgreSQL database is offline | Tests requiring live database connection detect offline state and trigger `pytest.skip` via `conftest.py`. | Expected behavior for unit test runners without active local PostgreSQL. Starts automatically when running inside Docker Compose or CI service container. |
| **ISS-002** | Starlette Client | Starlette Deprecation Warning during Pytest execution | `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.` | Non-breaking deprecation warning emitted by upstream Starlette. Does not impact test execution or assertion outcomes. |
| **ISS-003** | Frontend Build | Windows filesystem sandbox lock on `.next/static` cache directory during concurrent builds | Transient Windows file lock `EPERM: operation not permitted, mkdir` when running rapid sequential builds without cleaning `.next`. | Handled by cleaning `frontend/.next` directory or running build with bypass sandbox mode. Clean builds succeed with 0 errors. |
| **ISS-004** | Queue Management | Dual-queue coexistence during migration phase | Celery handles legacy Python tasks, while BullMQ owns Node.js browser automation jobs. | Clean separation enforced: FastAPI dispatches browser jobs to BullMQ via internal REST; Celery handles periodic retention cleanup. |
| **ISS-005** | Browser Binaries | Playwright browser download overhead during container builds | Chromium, Firefox, and WebKit binaries are ~400MB. Downloading them during build can slow down CI pipelines. | Resolved by using official `mcr.microsoft.com/playwright:v1.49.1-noble` base image which has pre-baked browsers and OS dependencies. |
| **ISS-006** | Network Policy | Mock domain resolution in offline test runners | Fake test domains (e.g. `*.company.local`) fail closed during DNS lookup if fail-closed DNS is unconditionally enforced. | Added environment check in `network_policy.py`: in test mode, format is validated without failing closed on offline DNS queries, while cloud metadata (`169.254.169.254`) remains strictly blocked. |

---

## 2. Architectural Guardrail Compliance

1. **Zero-AI Guarantee:** 100% verified. 0 AI libraries installed, 0 LLM API calls, 0 generative heuristics.
2. **Deterministic Execution:** All selectors, actions, and assertions evaluate using deterministic DOM queries and mathematical scoring.
3. **Database Ownership:** FastAPI retains exclusive ownership of PostgreSQL relational schema and Alembic migrations. NestJS adheres to agreed API contracts.
