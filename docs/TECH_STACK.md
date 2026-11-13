# Technology Stack & Dependency Specification

**Document Version:** 3.0.0  
**Project:** AutomationTestingWithAgentBrowser  
**Status:** Approved Specification  
**Enforcement:** Strict Zero-AI Policy  

---

## 1. System Technology Matrix

| Layer | Primary Technology | Version | Purpose & Responsibilities |
|---|---|---|---|
| **Frontend Framework** | Next.js (App Router) | 16.x LTS | Server/Client components, routing, UI layouts |
| **Frontend Runtime** | React & React DOM | 19.x | Component lifecycle, virtual DOM, reactivity |
| **Language (Frontend)** | TypeScript | 5.7+ | Strict compile-time typing and data contracts |
| **Styling & Theme** | Tailwind CSS | 3.4+ | Utility-first styling with dark/light themes |
| **UI Component Primitives** | Radix UI / Shadcn UI | Latest | Accessible modal, dropdown, tooltip primitives |
| **Visual Workflow Graph** | @xyflow/react (React Flow) | 12.12+ | Drag-and-drop canvas, custom nodes/edges, minimap |
| **Data Visualization** | Recharts | 3.10+ | Execution timeline metrics, pass/fail trends |
| **Icons** | Lucide React | 1.71+ | Clean, consistent enterprise icon system |
| **Main Backend Framework**| FastAPI (Python) | 0.115+ | REST APIs, authentication, RBAC, DB orchestration |
| **Language (Backend)** | Python | 3.12 - 3.15 | Strict type annotations, async/await |
| **ORM & Relational Access**| SQLAlchemy | 2.0+ | Type-safe declarative models, transactions, pooling |
| **Schema Migrations** | Alembic | 1.13+ | Version-controlled, idempotent PostgreSQL migrations |
| **Data Validation (Python)**| Pydantic v2 | 2.10+ | Request/response DTO parsing, validation |
| **Automation Backend** | NestJS (Node.js) | 10.x | Modular architecture, DI, internal execution APIs |
| **Language (Automation)** | TypeScript | 5.7+ | Strict typing, interfaces, Zod schema validation |
| **Automation Engine** | Playwright (TypeScript) | 1.49+ | Native DevTools protocol, Chromium, Firefox, WebKit |
| **Job Queue & Workers** | BullMQ | 5.x | Redis-backed distributed jobs, retries, concurrency |
| **Primary Database** | PostgreSQL | 16-alpine | Central ACID relational data store (19+ tables) |
| **In-Memory Broker & Cache**| Redis | 7-alpine | Queue transport, pub/sub event distribution |
| **Python Testing** | Pytest | 8.0+ | Unit, API, and integration test coverage |
| **Node.js Testing** | Jest & ts-jest | 29.x | Unit and service tests for automation service |
| **End-to-End Testing** | Playwright Test | 1.49+ | Full browser acceptance and smoke verification |
| **Containerization** | Docker & Compose | 3.8 Spec | Multi-container reproducible environments |

---

## 2. Zero-AI Architecture & Blacklist

To strictly comply with company data protection policies, the codebase enforces an absolute ban on all artificial intelligence technologies, models, heuristics, and external generative APIs.

### 2.1 Prohibited Technologies (Blacklist)
- **External AI Providers:** OpenAI (GPT-4, ChatGPT), Anthropic (Claude), Google Gemini / Vertex AI, Mistral, Groq, Cohere, Perplexity.
- **Local AI Frameworks:** Ollama, vLLM, llama.cpp, LocalAI, HuggingFace Transformers, PyTorch, TensorFlow.
- **AI-Powered Libraries:** LangChain, LlamaIndex, AutoGPT, CrewAI, AutoGen, Semantic Kernel, Browser-Use.
- **Non-Deterministic Heuristics:** AI-generated CSS/XPath selectors, LLM self-healing, probabilistic visual guessing, fuzzy non-algorithmic assertions.

### 2.2 Approved Deterministic Replacements
- **Selector Resolution:** Playwright accessible roles, accessible names, test IDs (`data-testid`), exact text matching, and explicitly configured CSS/XPath.
- **Change Detection:** Multi-factor algorithmic comparison using Levenshtein distance (RapidFuzz), DOM tree tree-edit distances, attribute fingerprinting, and ancestor Jaccard similarity.
- **Self-Healing Approval:** Candidate replacements are calculated with transparent mathematical scoring and queued for explicit human review. Silent automatic changes are strictly forbidden.

---

## 3. Node.js & NestJS Service Dependencies (`automation-service`)

### Core Production Dependencies
```json
{
  "dependencies": {
    "@nestjs/common": "^10.4.0",
    "@nestjs/core": "^10.4.0",
    "@nestjs/platform-express": "^10.4.0",
    "@nestjs/config": "^3.3.0",
    "@nestjs/bullmq": "^10.2.0",
    "bullmq": "^5.25.0",
    "ioredis": "^5.4.0",
    "playwright": "^1.49.0",
    "zod": "^3.24.0",
    "pg": "^8.13.0",
    "uuid": "^10.0.0",
    "ws": "^8.18.0",
    "winston": "^3.17.0"
  },
  "devDependencies": {
    "@nestjs/cli": "^10.4.0",
    "@nestjs/schematics": "^10.4.0",
    "@nestjs/testing": "^10.4.0",
    "@types/node": "^22.10.0",
    "@types/jest": "^29.5.0",
    "@types/uuid": "^10.0.0",
    "@types/ws": "^8.5.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.2.0",
    "typescript": "^5.7.0"
  }
}
```

---

## 4. Python Backend Dependencies (`backend/requirements.txt`)

```text
fastapi>=0.115,<1
uvicorn>=0.30,<1
pydantic>=2.0,<3
sqlalchemy>=2.0,<3
psycopg[binary]>=3.1,<4
pg8000>=1.31,<2
alembic>=1.13,<2
python-dotenv>=1.0,<2
rapidfuzz>=3.0,<4
cryptography>=42.0,<45
pyjwt>=2.8,<3
bcrypt>=4.0,<5
celery>=5.4,<6
redis>=5.0,<9
croniter>=2.0,<8
pytest>=8.0
httpx>=0.27
```

