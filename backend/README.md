# SaaS backend

Run from the repository root:

```powershell
python -m pip install -r .\backend\requirements.txt
python -m backend
```

PostgreSQL is the configured database, using the pure-Python `pg8000` driver.
The backend automatically loads the
repository-root `.env` file:

```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/obscura"
python -m backend
```

Create the database once with `createdb obscura` or PostgreSQL pgAdmin. The
backend creates its application tables on startup. Set a strong `JWT_SECRET`
before exposing the API beyond localhost. SQLite remains available for isolated
local smoke tests by setting `DATABASE_URL=sqlite:///./reports/saas.sqlite3`.
