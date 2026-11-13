# Software Requirements Specification (SRS)

**Document Version:** 3.0.0  
**Project:** AutomationTestingWithAgentBrowser  
**Status:** Approved Requirements Baseline  

---

## 1. Functional Requirements

### 1.1 Authentication & Multi-Tenant Authorization (RBAC)
- **REQ-AUTH-001:** The system shall authenticate users via cryptographically secure JWTs with configurable expiration and refresh token rotation.
- **REQ-AUTH-002:** The system shall enforce a 6-tier Role-Based Access Control model:
  - `Super Admin`: Global platform administration, user management, global configuration.
  - `Organization Admin`: Organization-level billing, project provisioning, member role management.
  - `Project Admin`: Project-level settings, environment secret configuration, member permissions.
  - `Developer`: Create, edit, publish workflows, define test cases, run manual executions.
  - `Tester`: Execute test suites, view execution logs, generate reports, approve selector updates.
  - `Viewer`: Read-only access to published flows, test cases, execution reports, and audit logs.
- **REQ-AUTH-003:** The system shall enforce project-level access boundaries; users shall not access or execute resources in projects they are not explicitly assigned to.
- **REQ-AUTH-004:** Passwords shall be hashed using secure algorithms (bcrypt/scrypt) with salted keys.

### 1.2 Project & Environment Management
- **REQ-ENV-001:** Support multiple environments per project (`Development`, `QA`, `Staging`, `Production`, `Custom`).
- **REQ-ENV-002:** Each environment must define a `base_url`, `allowed_domains` allowlist, custom timeouts, and encrypted secrets.
- **REQ-ENV-003:** Environment secrets must be encrypted at rest using AES-256-GCM.
- **REQ-ENV-004:** Plaintext secrets must never be leaked into execution logs, DOM snapshots, or reporting JSON payloads.

### 1.3 Visual Flow Builder (React Flow)
- **REQ-FLOW-001:** Visual canvas supporting drag-and-drop node creation, edge wiring, node deletion, pan, zoom, and undo/redo.
- **REQ-FLOW-002:** Support 7 node categories with 35+ specialized node types:
  - **Browser Nodes:** Launch Browser, Close Browser, New Tab, Switch Tab, Navigate URL, Reload Page, Back, Forward.
  - **Interaction Nodes:** Click, Double Click, Right Click, Hover, Fill, Type, Clear, Select Option, Check, Uncheck, Press Key, Scroll, Drag and Drop, Upload File.
  - **Selector Nodes:** Get By Role, Get By Label, Get By Text, Get By Placeholder, Get By Test ID, CSS Selector, XPath Selector.
  - **Assertion Nodes:** Element Visible, Element Hidden, Element Enabled, Element Disabled, Text Equals, Text Contains, URL Equals, URL Contains, Title Equals, Element Count, Attribute Equals, Input Value Equals, Screenshot Comparison.
  - **Control-Flow Nodes:** If/Else, Switch, For Each, Wait Delay, Retry Policy, Group.
  - **Data Nodes:** Set Variable, Get Variable, Environment Variable, Generate Test Data, Read CSV, JSON Input, API Request, Extract Text, Extract Attribute.
  - **Utility Nodes:** Screenshot, Log Message, Wait for Timeout, Wait for Network Idle, Execute JavaScript (sandboxed).
- **REQ-FLOW-003:** The canvas and backend must validate graph topological validity prior to execution (detecting cycles, missing connections, and orphan nodes).
- **REQ-FLOW-004:** Real-time visual node highlighting indicating execution states: `pending`, `running`, `passed`, `failed`, `skipped`.

### 1.4 Playwright Automation Engine (`automation-service`)
- **REQ-ENG-001:** Primary browser automation engine must be Playwright using TypeScript native APIs controlling Chromium, Firefox, and WebKit.
- **REQ-ENG-002:** Every execution run must execute inside an ephemeral, completely isolated `BrowserContext`. No shared cookies, cache, or storage across executions.
- **REQ-ENG-003:** Automation engine must rely on Playwright's native auto-waiting and actionability checks (visible, stable, enabled, editable). Fixed sleeps are prohibited as default synchronization.
- **REQ-ENG-004:** Deterministic selector resolution must prioritize accessible locators (`data-testid`, role+name, label, placeholder, text) before falling back to CSS or XPath.
- **REQ-ENG-005:** Multiple element matches must fail deterministically with an ambiguity error rather than silently acting on the first matched element.

### 1.5 Application Change Detection & Selector Maintenance
- **REQ-CHG-001:** When an element selector fails to locate a target, the engine must capture the failed locator, current DOM state, and compare it against saved selector baselines.
- **REQ-CHG-002:** The system must compute deterministic multi-factor similarity scores (tag, role, accessible name, stable attributes, ancestor hierarchy) using mathematical scoring.
- **REQ-CHG-003:** The platform shall NEVER automatically modify selectors silently. Candidate replacements must be submitted to the human review approval queue.
- **REQ-CHG-004:** Approved selector updates must create an immutable version entry in `locator_history` and trigger regression verification.

### 1.6 Execution Queue & Concurrency Management
- **REQ-QUEUE-001:** Execution workloads must be managed by BullMQ backed by Redis.
- **REQ-QUEUE-002:** Support priority queueing, concurrency limits per project/worker, execution timeouts, and cancellation requests.
- **REQ-QUEUE-003:** Implement job idempotency keys to prevent duplicate execution triggers.
- **REQ-QUEUE-004:** Non-idempotent browser actions (e.g., payment submission, destructive deletion) must not be blindly retried on failure.

### 1.7 Live Browser Monitoring
- **REQ-MON-001:** Provide a real-time monitor displaying active URL, page title, current step, duration, live logs, and streaming viewport images.
- **REQ-MON-002:** Viewport capture must be driven directly by the worker-owned Playwright page session; external processes shall not open separate browser sessions to spy on the viewport.
- **REQ-MON-003:** Internal browser debugging ports (e.g., Chrome CDP 9222) must never be exposed publicly.
- **REQ-MON-004:** WebSocket connections must support client reconnections and event replay.

### 1.8 Reporting & Artifacts
- **REQ-REP-001:** Generate comprehensive reports containing step timings, pass/fail status, console errors, network failures, screenshots, and Playwright traces.
- **REQ-REP-002:** Artifacts must be stored on persistent volumes (or Azure Blob / S3 compatible object storage) with SHA-256 integrity verification.
- **REQ-REP-003:** Reports must be exportable in structured JSON and standalone offline HTML formats.

---

## 2. Non-Functional Requirements

- **NFR-SEC-001:** Strict Zero-AI architecture; complete absence of third-party AI APIs, LLM calls, and probabilistic heuristics.
- **NFR-SEC-002:** SSRF Protection: strict rejection of RFC 1918 subnets, cloud metadata IPs (`169.254.169.254`, `fd00:ec2::254`), and unauthorized domains in production.
- **NFR-PERF-001:** API response times for CRUD endpoints < 150ms at 95th percentile.
- **NFR-PERF-002:** Browser worker startup and context creation overhead < 800ms.
- **NFR-REL-001:** Stalled worker recovery: BullMQ must detect stalled worker processes and mark executions as failed or trigger controlled recovery.

