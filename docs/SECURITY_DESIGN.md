# Security Design & Zero-AI Data Protection Policy
**Document Version:** 1.0.0  
**Effective Date:** November 9, 2026  
**Classification:** Confidential — Internal Enterprise Policy  
**System:** AutomationTestingWithAgentBrowser  

---

## 1. Zero-AI Company Data Protection Policy

### 1.1 Mandatory Policy Statement
Company data, source code, DOM trees, user credentials, execution logs, screenshots, and test artifacts must **NEVER** be processed by, submitted to, or analyzed by artificial intelligence (AI), machine learning (ML), large language models (LLMs), or external AI cloud providers.

This policy applies strictly to:
- External cloud AI APIs (OpenAI, Anthropic Claude, Google Gemini, Azure OpenAI, AWS Bedrock).
- Locally hosted or private LLM inference engines (Ollama, vLLM, LocalAI, LM Studio, llama.cpp).
- Browser-embedded AI models or AI-based web scrapers.
- AI-based selector generators or self-healing heuristics.
- Third-party AI telemetry, telemetry beacons, or error analytics SDKs.

### 1.2 Strictly Prohibited Packages & Endpoints
The following packages and dependencies are **prohibited from being installed or imported** in any tier of the application:
- `openai`, `anthropic`, `google-generativeai`, `google-genai`, `langchain`, `langchain-core`, `llama-index`, `ollama`, `transformers`, `torch`, `onnxruntime`, `ai-gateway`.
- In `package.json`: `ai`, `@ai-sdk/*`, `@langchain/*`, `openai`.

**Prohibited Configuration Variables:**
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OLLAMA_ENDPOINT`, `OLLAMA_MODEL`, `AI_GATEWAY_*`.

### 1.3 Immediate Remediation Plan (Phase 0 Audit Finding)
During the initial repository inspection, the files `.env` and `.env.example` were discovered to contain:
```bash
# Optional Ollama configuration for dynamic recognition workers
OLLAMA_ENDPOINT=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```
**Action Taken:** These lines are flagged as strict policy violations and are scheduled for immediate deletion from `.env` and `.env.example`. All element recognition and self-healing will be powered exclusively by deterministic algorithms.

---

## 2. Deterministic Substitutes for AI Capabilities

To meet all enterprise requirements without AI, the platform implements mathematically verifiable, deterministic algorithms:

| Traditional AI Automation Feature | Prohibited AI Method | Deterministic Enterprise Alternative in This Platform |
| :--- | :--- | :--- |
| **Element Recognition** | LLM prompt analysis of DOM | Multi-attribute scoring based on ARIA roles, accessible names, stable HTML attributes, and label bindings. |
| **Self-Healing Selectors** | AI vision or LLM text guessing | Multi-factor weighted confidence scoring engine with strict threshold gating ($\ge 95\%$ auto-heal, $85-94\%$ review). |
| **Text Matching & Similarity** | Vector embeddings / cosine similarity | RapidFuzz / Levenshtein string distance algorithm (normalized ratio) as minor supporting evidence ($5\%$ weight). |
| **DOM Structural Analysis** | Deep learning graph networks | Tree hierarchy fingerprinting (ancestor tags, sibling index, parent container tags). |
| **Flow Generation** | Generative AI prompt-to-flow | Visual React Flow drag-and-drop builder with validated Pydantic DAG schemas. |
| **Test Case Authoring** | Copilot / AI Test generators | Visual Test Builder with deterministic step sequences and explicit assertion definitions. |

---

## 3. Secret & Credential Management

### 3.1 Architecture (`backend/app/security/secret_manager.py`)
- Credentials (passwords, API tokens, client secrets, basic auth) required by automated workflows are stored encrypted in the PostgreSQL `credentials` table.
- **Encryption Standard:** AES-256-GCM authenticated encryption using an application master key (`APP_ENCRYPTION_KEY`).
- Secrets are decrypted in-memory only during the instant of execution dispatch.
- Decrypted secrets are **never** passed to command-line parameters in plain text where system process tables (`ps`, `Get-Process`) could expose them. They are injected via temporary named pipes or environment variables isolated to the execution subprocess.

### 3.2 Key Hierarchy
1. `APP_ENCRYPTION_KEY`: 256-bit key provided via environment variable (or hardware security module / KMS in production).
2. Credential Ciphertext: Initialization vector (IV 12 bytes) + Ciphertext + Authentication Tag (16 bytes).

---

## 4. Deterministic Redaction Engine

### 4.1 Log & Error Redaction (`backend/app/security/redaction.py`)
All execution logs, error messages, and step results are processed through a deterministic redaction pipeline before database persistence or WebSocket broadcast:
1. **Registered Secrets Scrubbing:** Every credential value active in the current project or execution is added to an exact-match replacement list and replaced with `[REDACTED_SECRET]`.
2. **Regex Pattern Scrubbing:**
   - Bearer / JWT tokens: `Bearer\s+[A-Za-z0-9\-_\.=]+` $\to$ `Bearer [REDACTED_TOKEN]`
   - API keys and hashes: `(?i)(api[_-]?key|secret|token|password|passwd|pwd)[\s:=]+([^\s,;]+)` $\to$ `$1: [REDACTED]`
   - Email addresses (configurable): `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}` $\to$ `[REDACTED_EMAIL]`
   - Credit card numbers / PANs: `\b(?:\d{4}[-\s]?){3}\d{4}\b` $\to$ `[REDACTED_CARD]`
   - Custom project-level regex patterns.

### 4.2 Screenshot & Visual Artifact Protection
- Screenshots taken during execution are saved to disk with restricted file permissions (`chmod 0600`).
- Access to screenshot files requires an authenticated API call with project-level read permissions (`artifacts:read`).
- Screenshots cannot be viewed by unauthenticated users or users lacking explicit project membership.

---

## 5. Network Policy & SSRF Prevention

### 5.1 Browser Domain Whitelisting (`backend/app/security/network_policy.py`)
To prevent automated flows from navigating to untrusted external sites, internal metadata endpoints, or cloud backplanes:
1. **Native Agent Browser Domain Restriction:**
   The `AGENT_BROWSER_ALLOWED_DOMAINS` environment variable is enforced for all spawned browser sessions.
2. **URL Validation Engine:**
   Before any `navigate` or `open` action is executed:
   - The destination URL is parsed.
   - Scheme must be `http` or `https` (prevent `file://`, `gopher://`, `javascript:`, `data:` exploits).
   - Hostname is resolved against an SSRF filter:
     - Deny `127.0.0.0/8` (loopback) unless explicitly allowed for local testing environment.
     - Deny `169.254.169.254` (cloud metadata service).
     - Deny `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (RFC 1918 private subnets) unless whitelisted in the active Environment configuration.
     - Domain must match the environment's `allowed_domains` glob pattern list (e.g. `*.mycompany.com`, `staging.internal.app`).

---

## 6. Role-Based Access Control (RBAC)

The application enforces fine-grained permissions across all resources:

### 6.1 Role Definitions
- **Owner:** Full system administrative rights, tenant management, audit log access, system-wide settings.
- **Admin:** User and environment configuration, credential lifecycle, role assignment.
- **Developer:** Design, edit, publish, and delete automation flows, test cases, and element profiles.
- **Tester:** Execute flows and tests, inspect execution logs, view reports, request self-healing approvals.
- **Viewer:** Read-only access to dashboards, test matrices, and execution summaries.

### 6.2 Permissions Matrix

| Permission Key | Owner | Admin | Developer | Tester | Viewer |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `users:manage` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `environments:write` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `credentials:manage` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `flows:create_edit` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `flows:publish` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `tests:create_edit` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `executions:trigger` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `executions:cancel` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `healing:approve` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `reports:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `artifacts:download` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `audit_logs:read` | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 7. Artifact Lifecycle & Retention Policy

### 7.1 Retention Rules (`backend/app/security/retention.py`)
Automated cleanup tasks run daily to purge old assets based on project settings:
- **Execution Logs:** Retained for 90 days (default) or configurable per project.
- **Screenshots:** Retained for 30 days unless pinned to a failed execution report.
- **DOM Snapshots:** Retained for 14 days (raw DOM snapshots contain rendered enterprise data).
- **Audit Logs:** Immutable; retained for a minimum of 365 days.

---

## 8. Audit Logging Specification

### 8.1 Tracked Security Events (`backend/app/security/audit.py`)
All critical operations emit an immutable record to the `audit_logs` table:
- Authentication events (login success, login failure, token issuance).
- User management (user creation, role change, deactivation).
- Credential management (credential added, updated, accessed).
- Flow & Test publication (new version published, draft archived).
- Self-Healing actions (auto-healed locator applied, healing approval granted/denied).
- Execution triggers (manual run, scheduled run, cancellation).

Every audit log entry records: `timestamp_utc`, `user_id`, `client_ip`, `action`, `resource_type`, `resource_id`, and `metadata_json`.

