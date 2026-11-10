"""REST API endpoints for Credentials Vault (/api/v1/credentials)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.project import Credential, Project
from backend.app.models.user import User
from backend.app.api.v1.projects import resolve_project_id
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission
from backend.app.security.secret_manager import SecretManager

router = APIRouter(prefix="/credentials", tags=["Credentials"])


class CredentialCreateSchema(BaseModel):
    project_id: UUID | str
    name: str = Field(..., min_length=2, max_length=120)
    credential_type: str = Field(..., pattern=r"^(username_password|api_token|bearer_token)$")
    username: str | None = None
    secret_value: str = Field(..., min_length=1)
    domain_scope: str | None = None


@router.get("", response_model=list[dict[str, Any]])
def list_credentials(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_credentials")),
) -> list[dict[str, Any]]:
    """List stored credentials metadata. Raw secrets are NEVER returned."""
    query = db.query(Credential)
    if project_id:
        proj = resolve_project_id(db, project_id)
        if proj:
            query = query.filter(Credential.project_id == proj.id)
    creds = query.all()

    return [
        {
            "id": str(c.id),
            "project_id": str(c.project_id),
            "name": c.name,
            "credential_type": c.credential_type,
            "username": c.username,
            "domain_scope": c.domain_scope,
            "is_encrypted": True,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in creds
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_credentials")),
) -> dict[str, Any]:
    """Store encrypted credential. Secret is write-only AES-256 encrypted."""
    project = resolve_project_id(db, payload.project_id, current_user.id)
    if not project:
        raise HTTPException(status_code=404, detail="Target project not found")

    encrypted_secret = SecretManager.encrypt(payload.secret_value)

    new_cred = Credential(
        project_id=project.id,
        name=payload.name.strip(),
        credential_type=payload.credential_type,
        username=payload.username.strip() if payload.username else None,
        secret_encrypted=encrypted_secret,
        domain_scope=payload.domain_scope.strip() if payload.domain_scope else None,
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="credential_created",
        resource=f"Credential:{new_cred.id}",
        details={"name": new_cred.name, "type": new_cred.credential_type},
        result="success",
    )

    return {
        "id": str(new_cred.id),
        "name": new_cred.name,
        "credential_type": new_cred.credential_type,
        "domain_scope": new_cred.domain_scope,
        "status": "encrypted",
    }


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_credentials")),
) -> None:
    """Permanently revoke and delete a credential."""
    cred = db.query(Credential).filter(Credential.id == credential_id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    db.delete(cred)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="credential_deleted",
        resource=f"Credential:{credential_id}",
        details={"name": cred.name},
        result="success",
    )
