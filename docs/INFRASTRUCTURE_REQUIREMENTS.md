# Infrastructure & Operational Requirements Specification

**Document Version:** 3.0.0  
**Project:** AutomationTestingWithAgentBrowser  
**Status:** Approved Infrastructure Baseline  

---

## 1. Development & Production Sizing Guidelines

| Parameter | Development Environment | Production Baseline (Starting) | Production Scaled Tier |
|---|---|---|---|
| **Operating System** | Windows 11 / macOS / Linux | Ubuntu 22.04 LTS / Debian 12 | Enterprise Linux / Container Host |
| **Node.js Runtime** | Node.js 22 LTS | Node.js 22 LTS | Node.js 22 LTS Container |
| **Python Runtime** | Python 3.12 - 3.15 | Python 3.12 Container | Python 3.12 Container |
| **CPU Cores** | 4 Cores minimum | 8 vCPUs | 16-32 vCPUs (Distributed Workers) |
| **System Memory (RAM)** | 8 GB minimum (16 GB rec.) | 16 - 32 GB | 64 GB+ (Dedicated Worker Nodes) |
| **Storage (SSD)** | 30 - 50 GB NVMe | 100 - 250 GB SSD | Managed Object Store (S3/Azure Blob)|
| **Browser Concurrency** | 1 - 2 active sessions | 4 - 8 active sessions per node | 16 - 32 distributed sessions |
| **Database** | Local PostgreSQL 16 | PostgreSQL 16 (Dedicated/HA) | Managed PostgreSQL (Azure/AWS RDS) |
| **Cache & Queue Broker** | Local Redis 7 | Dedicated Redis 7 with AOF | Managed Redis (Cluster / Sentinel) |

---

## 2. Containerized Architecture & Services (`docker-compose.yml`)

The enterprise platform runs via Docker Compose with dedicated service definitions:

```
+----------------------------------------------------------------------------------------------------+
|                                    Docker Compose Network: app_net                                 |
|                                                                                                    |
|  +--------------------+   +--------------------+   +--------------------+   +-------------------+  |
|  |      frontend      |   |      backend       |   |   automation-api   |   | automation-worker |  |
|  |     (Next.js)      |   |     (FastAPI)      |   |      (NestJS)      |   | (NestJS+Playwright|  |
|  |    Port: 3000      |   |    Port: 8000      |   |    Port: 3001      |   |  Internal Only    |  |
|  +---------+----------+   +---------+----------+   +---------+----------+   +---------+---------+  |
|            |                        |                        |                        |            |
|            +------------------------+                        +------------------------+            |
|                                     |                                                 |            |
|                           +---------v----------+                           +----------v---------+  |
|                           |      postgres      |                           |       redis        |  |
|                           |  (PostgreSQL 16)   |                           |     (Redis 7)      |  |
|                           |    Port: 5432      |                           |    Port: 6379      |  |
|                           +--------------------+                           +--------------------+  |
|                                                                                                    |
|  Persistent Volumes: `postgres_data`, `reports_storage`, `playwright_traces`                       |
+----------------------------------------------------------------------------------------------------+
```

### Service Health Checks & Isolation Rules
1. **PostgreSQL (`postgres`):**
   - Healthcheck: `pg_isready -U postgres -d automation_platform_db`
   - Volume: `postgres_data:/var/lib/postgresql/data`
2. **Redis (`redis`):**
   - Healthcheck: `redis-cli ping`
   - Data persistence: Append-Only File (AOF) enabled.
3. **FastAPI Backend (`backend`):**
   - Healthcheck: `curl -f http://localhost:8000/health`
   - Depends on: `postgres` (healthy), `redis` (healthy).
4. **NestJS Automation API (`automation-api`):**
   - Healthcheck: `curl -f http://localhost:3001/health`
   - Depends on: `redis` (healthy), `backend` (healthy).
5. **NestJS Browser Workers (`automation-worker`):**
   - Headless Playwright worker container.
   - Resource limits: Max 2GB memory per worker process; `shm_size: '2gb'` to prevent Chromium `/dev/shm` exhaustion.
   - Restricted privileges: Non-root user `pwuser`, strictly isolated from host filesystem.
6. **Next.js Frontend (`frontend`):**
   - Port 3000. Depends on `backend` (healthy).

---

## 3. Storage Hierarchy & Retention Policies

- **Database Relational Storage:** PostgreSQL handles metadata, user accounts, flow graphs, step execution statuses, selector fingerprints, and audit logs.
- **Artifact Local Storage (`/app/reports`):**
  - Screenshots: `/app/reports/screenshots/{execution_id}/{step_id}.png`
  - Playwright Traces: `/app/reports/traces/{execution_id}.zip`
  - Full Page DOM Snapshots: `/app/reports/dom/{execution_id}/{step_id}.json`
  - Consolidated HTML Reports: `/app/reports/html/{execution_id}.html`
- **Tamper-Evidence:** Every stored file artifact generates a cryptographically signed SHA-256 hash stored in PostgreSQL table `artifacts`.
- **Retention Lifecycle:** Celery Beat / scheduled cron invokes automated cleanup removing artifacts older than project-defined retention limits (e.g., 30 days) while preserving audit logs.

