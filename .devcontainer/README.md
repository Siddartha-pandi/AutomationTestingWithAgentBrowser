# Development Container Guide

This repository includes a pre-configured **Visual Studio Code / Cursor Dev Container**. It gives every team member an identical, fully reproducible development environment with:

- **Python 3.11** + virtual environment + all backend dependencies (`FastAPI`, `SQLAlchemy 2.0`, `Celery`, `Alembic`, etc.)
- **Node.js 20 LTS** + all frontend dependencies (`Next.js 14`, `Tailwind CSS`, `Lucide React`, etc.)
- **agent-browser CLI v0.41.2** with Linux Chromium/Playwright system rendering dependencies pre-installed
- **PostgreSQL 16** container pre-migrated with Alembic & seeded with default enterprise roles and admin user
- **Redis 7** container for Celery asynchronous task distribution
- Pre-configured VS Code extensions (Python, Pylance, Prettier, Tailwind, ESLint, SQLTools)

---

## 🚀 Quick Start for Teammates

### 1. Prerequisites
Ensure your machine has:
1. **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** installed and running.
2. **[Visual Studio Code](https://code.visualstudio.com/)** or **Cursor**.
3. The **[Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)** (`ms-vscode-remote.remote-containers`) installed in VS Code.

---

### 2. Open the Project in Dev Container
1. Open the project folder in VS Code / Cursor:
   ```bash
   code .
   ```
2. A pop-up will appear in the bottom-right corner:
   > *"Folder contains a Dev Container configuration file. Reopen in Container?"*
3. Click **"Reopen in Container"**.
   *(Alternatively: Press `F1` or `Ctrl+Shift+P`, type `Dev Containers: Reopen in Container`, and press Enter).*
4. VS Code will build the container, start Postgres & Redis, install dependencies, run migrations, and seed test data automatically.

---

### 3. Running Services Inside the Dev Container

Once VS Code connects into the container, open a terminal (`Ctrl+` `~`) and run:

#### Start the Backend API:
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
- API is accessible at: [http://localhost:8000](http://localhost:8000)
- Swagger Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Start the Celery Asynchronous Worker (in a second terminal):
```bash
celery -A backend.app.worker.celery_app worker -l INFO
```

#### Start the Next.js Frontend (in a third terminal):
```bash
cd frontend
npm run dev -- -p 3001
```
- UI is accessible at: [http://localhost:3001](http://localhost:3001)

#### Run Test Suites:
```bash
pytest
```

---

## 🔑 Default Seeded Admin Credentials

| Field | Value |
|---|---|
| **Email** | `admin@enterprise.local` |
| **Password** | `AdminPassword123!` |
| **Role** | Tenant Owner (`owner`) |
| **Project** | `Enterprise QA` |

---

## 🛠️ Port Forwarding Matrix

| Port | Description | Host Access |
|---|---|---|
| `8000` | FastAPI Backend API | `http://localhost:8000` |
| `3001` | Next.js Frontend Dashboard | `http://localhost:3001` |
| `5432` | PostgreSQL 16 Database | `localhost:5432` (`postgres:postgres`) |
| `6379` | Redis 7 Task Broker | `localhost:6379` |

