# Security & Data Protection Architecture Specification

**Document Version:** 3.0.0  
**Project:** AutomationTestingWithAgentBrowser  
**Status:** Approved Security Baseline  
**Classification:** Enterprise Confidential / Zero-AI Compliance  

---

## 1. Zero-AI Data Protection Policy

To guarantee zero leakage of proprietary code, customer credentials, internal network topologies, or enterprise testing artifacts:

1. **Zero External API Invocations:** No data, DOM snippets, or error traces shall ever be sent to any external AI endpoint (OpenAI, Anthropic, Google, Azure OpenAI, etc.).
2. **Zero In-Memory Models:** No local LLMs or machine learning heuristics run inside any platform container.
3. **Deterministic Verification:** Every test decision, assertion, and selector recovery is governed by inspectable, transparent, mathematical programming logic.

---

## 2. Multi-Tenant Role-Based Access Control (RBAC)

The system enforces authorization at both the global and project levels.

### Permission Matrix

| Role | Flows (Create/Edit) | Flows (Execute) | Test Suites (Run) | Secrets (Manage) | Selectors (Approve) | Audit Logs (Read) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Super Admin** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Org Admin** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Project Admin** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Developer** | Yes | Yes | Yes | No | Yes | No |
| **Tester** | No | Yes | Yes | No | Yes | Yes |
| **Viewer** | No | No | No | No | No | Yes |

### Project Boundary Isolation
- Every execution request is checked against `project_members`.
- Non-admin users cannot access, execute, or view workflows belonging to other projects.
- Database queries automatically filter results by user project memberships.

---

## 3. Secret Management & Cryptographic Protection

1. **Encryption at Rest:** Environment variables, API credentials, and authentication cookies are encrypted using **AES-256-GCM** with 96-bit random initialization vectors (IVs) and authentication tags.
2. **Key Derivation:** Master keys are derived from `APP_ENCRYPTION_KEY` using PBKDF2 or HKDF with a cryptographic salt.
3. **Deterministic Log Redaction:**
   - Secrets are identified and stored in a sensitive token registry.
   - All console logs, error messages, and network payloads pass through a redaction filter before being emitted to WebSockets or persisted to PostgreSQL.
   - Redacted secrets appear as `[REDACTED_SECRET_*****]`.

---

## 4. Server-Side Request Forgery (SSRF) Prevention

Browser automation nodes are strictly controlled to prevent attackers or rogue test scripts from pivoting into internal company networks or cloud metadata APIs.

### Blocked Subnets & Hostnames
- **Cloud Metadata Services:**
  - `169.254.169.254/32` (AWS/GCP/Azure IMDSv1/v2)
  - `fd00:ec2::254/128` (AWS IPv6 IMDS)
  - `169.254.0.0/16` (Link-local)
  - Hostnames: `metadata.google.internal`, `metadata.goog`, `instance-data`
- **Private Subnets (RFC 1918):**
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
  - Blocked by default in production unless explicitly allowed by environment network policy.
- **Loopback & Localhost:**
  - `127.0.0.0/8`, `::1/128`, `localhost`
  - Prohibited in production.
- **Fail-Closed DNS Validation:**
  - Hostnames in URLs are resolved before navigation. If any resolved IP belongs to a restricted range or if DNS resolution fails in production, navigation is aborted immediately.

---

## 5. Browser Sandbox & Container Isolation

- **Non-Root Execution:** Playwright browser instances run as non-root user `pwuser`.
- **Ephemeral Contexts:** Each execution creates a new `BrowserContext` with isolated cache, cookies, and local storage; contexts are destroyed immediately upon execution completion or abort.
- **Host Filesystem Isolation:** Worker containers mount only the designated `/app/reports` volume; no sensitive host paths (e.g., Docker socket `/var/run/docker.sock`) are mounted into worker containers.
- **Debugging Port Security:** Browser DevTools / CDP ports (9222) are bound strictly to localhost inside the worker container and are NEVER exposed to the public network or host.

