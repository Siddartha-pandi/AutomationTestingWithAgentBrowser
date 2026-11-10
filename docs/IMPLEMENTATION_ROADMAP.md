# Enterprise Implementation Roadmap: AutomationTestingWithAgentBrowser

**Document Version:** 1.0.0  
**Date:** November 10, 2026  
**Status:** Approved for Implementation  
**Policy Standard:** Zero-AI Company Data Protection Guarantee  
**Engine:** Agent Browser CLI Subprocess Adapter (`0.41.2`)  

---

## 1. Roadmap Architecture & Execution Principles

This roadmap outlines the ordered, phase-by-phase implementation plan to upgrade `AutomationTestingWithAgentBrowser` into an enterprise-grade automation and testing platform.

### Non-Negotiable Execution Rules:
1. **Never Replace Working Code:** Preserve all existing working modules, schemas, and UI components.
2. **Zero AI Policy:** No AI SDKs, LLM APIs, vector databases, or AI heuristics. All recognition and self-healing must remain 100% deterministic.
3. **Agent Browser Exclusivity:** `agent-browser` CLI remains the sole browser engine.
4. **Test After Every Step:** Backend APIs, frontend builds, and automated tests must pass at every milestone.

---

## 2. Phase-by-Phase Implementation Plan

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       UPGRADE IMPLEMENTATION TIMELINE                       │
├─────────┬─────────────────────────────────────────────────┬─────────────────┤
│ PHASE   │ OBJECTIVE                                       │ STATUS          │
├─────────┼─────────────────────────────────────────────────┼─────────────────┤
│ Phase 0 │ Existing Repository Audit & Gap Analysis        │ COMPLETED       │
│ Phase 1 │ Backend Startup & Test Lifecycle Stabilization  │ READY TO START  │
│ Phase 2 │ Sidebar & Global Application Layout Completion  │ PENDING PHASE 1 │
│ Phase 3 │ Automa / n8n Extended Action Catalog & Nodes    │ PENDING PHASE 2 │
│ Phase 4 │ WrightTest Browser Recorder Module              │ PENDING PHASE 3 │
│ Phase 5 │ Parameterized Test Data Management (CSV/JSON)   │ PENDING PHASE 4 │
│ Phase 6 │ Visual Flow Templates & Starter Library         │ PENDING PHASE 5 │
│ Phase 7 │ Database Multi-Tenancy (`project_members`)      │ PENDING PHASE 6 │
│ Phase 8 │ End-to-End Verification & Compliance Audit      │ FINAL STAGE     │
└─────────┴─────────────────────────────────────────────────┴─────────────────┘
```

---

### Phase 0: Audit & Architectural Blueprint (Completed)
- [x] Deep code inspection across `backend/`, `frontend/`, `reports/`, `alembic/`, `scripts/`, `tests/`.
- [x] Create `docs/EXISTING_PROJECT_AUDIT.md`.
- [x] Create `docs/FEATURE_GAP_ANALYSIS.md`.
- [x] Create `docs/IMPLEMENTATION_ROADMAP.md`.

---

### Phase 1: Backend Startup & Test Lifecycle Stabilization
**Objective:** Eliminate import-time database failures and enable reliable offline unit/integration test execution.
- [ ] **Migrate Database Init to FastAPI Lifespan:**
  - Update `backend/main.py`: replace top-level `initialize()` with async lifespan context manager.
  - Wrap database connection check in graceful try-except with configurable retry so test imports do not crash when running offline.
- [ ] **Pytest Environment Configuration:**
  - Ensure unit tests mock remote PostgreSQL connections when running in an isolated sandbox or offline environment.
  - Verify that `python scripts/verify_zero_ai_policy.py` passes with exit code 0.
- [ ] **Verify Verification Deliverable:**
  - `python scripts/verify_zero_ai_policy.py` returns `100% VERIFIED COMPLIANT`.
  - Pytest unit tests collect and execute without network resolution errors.

---

### Phase 2: Sidebar & Global Application Layout Completion
**Objective:** Align the UI shell exactly with Section 4 specifications by adding the missing navigation items and view routes.
- [ ] **Update Sidebar Navigation in `frontend/src/components/layout/AppShell.tsx`:**
  - Under **AUTOMATION**: Add `Flow Templates` (`automation_templates`).
  - Under **TESTING**: Add `Test Data` (`testing_data`).
  - Under **BROWSER INTELLIGENCE**: Add `Browser Recorder` (`browser_recorder`).
- [ ] **Update Workspace Dispatcher in `frontend/src/components/workspace/AuthenticatedWorkspace.tsx`:**
  - Route `automation_templates` to `FlowTemplatesPage`.
  - Route `testing_data` to `TestDataPage`.
  - Route `browser_recorder` to `BrowserRecorderPage`.
- [ ] **Verify Frontend Compilation:**
  - Run `npx tsc --noEmit` to guarantee 0 TypeScript errors.

---

### Phase 3: Automa & n8n Extended Action Catalog
**Objective:** Expand the Action Catalog with rich browser actions, data manipulation, and control flow nodes.
- [ ] **Extend `AgentBrowserAdapter` (`backend/app/browser/agent_browser.py`):**
  - Add `hover(session_id, selector)`.
  - Add `scroll(session_id, direction, amount, selector)`.
  - Add `right_click(session_id, selector)`.
  - Add `back(session_id)`, `forward(session_id)`, `reload(session_id)`.
  - Add explicit `check(session_id, selector)` and `uncheck(session_id, selector)`.
- [ ] **Update Flow Action Schemas (`backend/app/engine/flows/flow_schema.py`):**
  - Add new action types to `FlowActionType`: `HOVER`, `SCROLL`, `RIGHT_CLICK`, `BROWSER_BACK`, `BROWSER_FORWARD`, `REFRESH`, `CHECK`, `UNCHECK`, `SWITCH`, `STRING_OP`, `NUMBER_OP`, `JSON_OP`, `DATE_OP`, `ARRAY_OP`.
- [ ] **Implement Action Handlers in `ActionRegistry` (`backend/app/engine/flows/action_registry.py`):**
  - Implement deterministic execution logic for all new actions.
- [ ] **Update Visual Flow Builder UI (`frontend/src/components/flows/VisualFlowBuilder.tsx`):**
  - Group action palette into: **Browser Actions**, **Logic & Flow Control**, **Data Operations**, **Advanced Control**.
  - Provide configuration panels for all new node types.

---

### Phase 4: WrightTest Browser Recorder Module
**Objective:** Implement interactive browser session recording to generate Flows and Test Cases.
- [ ] **Backend Recorder Router (`backend/app/api/v1/recorder.py`):**
  - Endpoints:
    - POST `/api/v1/recorder/start`: Spawns dedicated recording session and navigates to target URL.
    - POST `/api/v1/recorder/stop`: Closes recording session and returns recorded action trail.
    - GET `/api/v1/recorder/status`: Polls current URL and recent interactive element states.
    - POST `/api/v1/recorder/action`: Ingests and verifies recorded user interaction.
    - POST `/api/v1/recorder/save`: Converts recorded action trail into an `AutomationDefinition` (Flow or Test Case).
- [ ] **Mount Recorder Router in `backend/app/api/v1/__init__.py`:**
  - Expose `/api/v1/recorder` in master API.
- [ ] **Frontend Recorder Component (`frontend/src/components/browser/BrowserRecorderPage.tsx`):**
  - Session launcher: URL input, environment picker, session start button.
  - Live interaction panel: screenshot stream, action history table with edit/delete capability.
  - "Save as Flow" and "Save as Test Case" export modals.

---

### Phase 5: Parameterized Test Data Management
**Objective:** Provide enterprise CSV/JSON test data management for data-driven testing.
- [ ] **Backend Test Data Endpoints:**
  - Add CSV/JSON upload, parse, and parameterization helpers to `/api/v1/tests`.
  - Ensure secret values in test data are automatically redacted from previews and execution logs.
- [ ] **Frontend Test Data Component (`frontend/src/components/testing/TestDataPage.tsx`):**
  - Dataset library: upload CSV, paste JSON, inline tabular data editor.
  - Bind datasets directly to Test Cases in `VisualTestBuilder.tsx`.

---

### Phase 6: Visual Flow Templates & Starter Library
**Objective:** Provide ready-to-run templates for common enterprise automation patterns.
- [ ] **Backend Template Catalog:**
  - Pre-load standard enterprise templates:
    1. Authentication & Cookie Verification Flow
    2. Data Entry & Form Submission Flow
    3. Multi-Row Table Scraper & CSV Exporter Flow
    4. End-to-End Regression Smoke Flow
- [ ] **Frontend Template Gallery (`frontend/src/components/flows/FlowTemplatesPage.tsx`):**
  - Card-based template browser with preview, tag filters, and "Use Template" one-click cloning into project.

---

### Phase 7: Multi-Tenancy & Project Members (`project_members`)
**Objective:** Complete database alignment with Section 12 and enforce granular project-level RBAC.
- [ ] **Database Migration:**
  - Create Alembic migration for `project_members` table: `(project_id, user_id, role, added_at)`.
- [ ] **Backend Project RBAC Enforcement:**
  - Update `backend/app/security/rbac.py` to enforce project membership and project-scoped permissions.
- [ ] **Frontend Project Members Management:**
  - Add member assignment UI to `ProjectsPage.tsx`.

---

### Phase 8: End-to-End Verification & Compliance Audit
**Objective:** Complete regression testing and final compliance sign-off.
- [ ] Run full pytest suite across all modules.
- [ ] Run frontend production build check (`npm run build`).
- [ ] Verify Zero-AI compliance auditor passes with 0 violations.
- [ ] Update `docs/USER_MANUAL.md` with new features and operational instructions.
- [ ] Present completed platform to user.
