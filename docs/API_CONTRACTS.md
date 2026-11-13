# API & Inter-Service Communication Contracts

**Document Version:** 3.0.0  
**Project:** AutomationTestingWithAgentBrowser  
**Status:** Approved API Contract Specification  

---

## 1. Internal Service Authentication (FastAPI <-> NestJS)

All internal API calls between FastAPI and the NestJS Automation Service must be authenticated using a cryptographically signed shared secret or internal HMAC token.

- **Header Name:** `X-Internal-Service-Key`
- **Correlation ID Header:** `X-Correlation-ID`
- **Timestamp Header:** `X-Request-Timestamp`
- **Replay Window:** Requests older than 300 seconds are rejected with `401 Unauthorized`.

---

## 2. Internal Execution Endpoints (NestJS Automation API)

### 2.1 Submit Browser Execution Job
- **Endpoint:** `POST /internal/v1/jobs/execute`
- **Description:** FastAPI dispatches an authorized, validated flow or test case execution into BullMQ.
- **Request Headers:**
  - `Content-Type: application/json`
  - `X-Internal-Service-Key: <INTERNAL_SERVICE_SECRET>`
  - `X-Correlation-ID: <UUID>`

#### Request Payload
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_id": "7b8f3d12-421b-4f9e-a89c-9c3132e1858a",
  "environment_id": "3c9b4e10-928a-4d7e-bf31-1e92d8f28124",
  "user_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "flow_id": "9d8e7f6a-5b4c-3d2e-1f0a-9b8c7d6e5f4a",
  "flow_version_num": 3,
  "browser_config": {
    "browser_type": "chromium",
    "headless": true,
    "viewport": {
      "width": 1280,
      "height": 800
    },
    "record_video": false,
    "record_trace": true,
    "timeout_ms": 30000
  },
  "allowed_domains": [
    "app.mycompany.com",
    "auth.mycompany.com"
  ],
  "variables": {
    "BASE_URL": "https://app.mycompany.com",
    "USERNAME": "test_qa_user"
  },
  "graph_definition": {
    "nodes": [
      {
        "id": "node-1",
        "type": "navigate",
        "config": {
          "url": "{{BASE_URL}}/dashboard"
        }
      },
      {
        "id": "node-2",
        "type": "click",
        "config": {
          "locator_strategy": "role",
          "role": "button",
          "name": "Submit"
        }
      }
    ],
    "edges": [
      {
        "source": "node-1",
        "target": "node-2"
      }
    ]
  }
}
```

#### Response (202 Accepted)
```json
{
  "status": "queued",
  "job_id": "bull-job-10492",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "correlation_id": "cor-839210-af",
  "queued_at": "2026-11-12T17:30:00.000Z"
}
```

---

### 2.2 Cancel Active Execution
- **Endpoint:** `POST /internal/v1/jobs/:execution_id/cancel`
- **Description:** Gracefully aborts an active browser execution context, closes Playwright pages, and saves partial artifacts.

#### Response (200 OK)
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "aborted_step_id": "node-2",
  "message": "Execution cancellation signal received and processed."
}
```

---

### 2.3 Get Worker Status & Health
- **Endpoint:** `GET /internal/v1/health`

#### Response (200 OK)
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "browsers_ready": {
    "chromium": true,
    "firefox": true,
    "webkit": true
  },
  "active_jobs": 2,
  "queue_depth": 0,
  "uptime_seconds": 14200
}
```

---

## 3. Real-Time WebSocket Event Contracts

WebSocket events are published to Redis channel `execution:events:{execution_id}` by the Playwright worker and consumed by FastAPI's WebSocket Gateway to stream to the Next.js frontend.

### Standardized Event Envelope
```json
{
  "event_id": "evt-7f8931ac-9201",
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "seq": 14,
  "timestamp": "2026-11-12T17:30:02.120Z",
  "type": "step:complete",
  "payload": {
    "node_id": "node-1",
    "action": "navigate",
    "status": "passed",
    "duration_ms": 482.5,
    "url": "https://app.mycompany.com/dashboard",
    "page_title": "Enterprise Dashboard"
  }
}
```

### Supported Event Types
1. `execution:status_change`: `queued` -> `running` -> `passed` / `failed` / `cancelled`
2. `step:start`: Node execution initiated.
3. `step:complete`: Node execution completed successfully.
4. `step:failed`: Node encountered an assertion failure, timeout, or error.
5. `viewport:frame`: Base64 JPEG frame of current worker-owned Playwright page.
6. `screenshot:captured`: High-resolution PNG artifact saved with URL path.
7. `console:log`: Browser console message or network failure logged.

