from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from backend.app.api.v1 import api_v1_router
from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.user import Role, User
from backend.app.security.audit import log_audit_event
from backend.app.security.jwt import create_access_token
from backend.app.security.password import hash_password, verify_password
from backend.app.security.rbac import get_current_user
from backend.config import settings
from backend.db import execute, initialize
from backend.schemas import AuthRequest, AuthResponse, RunResponse, WorkflowCreate, WorkspaceCreate

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown lifecycle."""
    try:
        initialize()
        logger.info("Database schema initialized and RBAC roles verified.")
    except Exception as err:
        logger.warning(
            "Database initialization deferred or unavailable at startup: %s. "
            "Application startup continuing; database calls will connect on demand.",
            err,
        )
    yield


app = FastAPI(
    title="AutomationTestingWithAgentBrowser",
    version="1.0.0",
    description="Deterministic Flow & Testing Automation Platform powered by Agent Browser",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

# Mount Versioned Enterprise APIs
app.include_router(api_v1_router)

# Mount Root WebSocket Monitoring endpoint
from backend.app.api.v1.ws_monitor import router as ws_monitor_router
app.include_router(ws_monitor_router)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "postgresql", "platform": "AutomationTestingWithAgentBrowser"}


# -----------------------------------------------------------------------------
# Backward-Compatible Legacy Endpoints
# -----------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def legacy_register(
    payload: AuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    email = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user_count = db.query(User).count()
    assigned_role_name = "owner" if user_count == 0 else "developer"
    role = db.query(Role).filter(Role.name == assigned_role_name).first()

    new_user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=email.split("@")[0].capitalize(),
        is_active=True,
        is_superuser=(user_count == 0),
        roles=[role] if role else [],
    )
    db.add(new_user)
    db.flush()

    project = Project(name=f"{email.split('@')[0]}'s workspace", owner_id=new_user.id)
    db.add(project)
    db.commit()
    db.refresh(new_user)

    roles_list = [r.name for r in new_user.roles]
    token = create_access_token(user_id=new_user.id, email=new_user.email, roles=roles_list)

    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return AuthResponse(token=token, user_id=1)


@app.post("/api/auth/login", response_model=AuthResponse)
def legacy_login(
    payload: AuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthResponse:
    email = payload.email.lower().strip()
    user = db.query(User).options(joinedload(User.roles)).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    roles_list = [r.name for r in user.roles]
    token = create_access_token(user_id=user.id, email=user.email, roles=roles_list)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return AuthResponse(token=token, user_id=1)


@app.get("/api/workspaces")
def list_workspaces(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    return [{"id": 1, "name": p.name, "created_at": p.created_at.isoformat()} for p in projects]
