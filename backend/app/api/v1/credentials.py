"""REST API endpoints for Credentials Vault (/api/v1/credentials).

AES-256-GCM authenticated encryption for passwords, API tokens, and bearer secrets.
Strict multi-tenant project isolation and domain scope verification.
"""

from __future__ import annotations

import fnmatch
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.api.v1.projects import resolve_project_id, user_has_project_access
from backend.app.db.session import get_db
from backend.app.models.project import Credential, Project, ProjectMember
from backend.app.models.user import User
from backend.app.security.audit import log_audit_event
from backend.app.security.rbac import get_current_user, require_permission
from backend.app.security.secret_manager import SecretManager

router = APIRouter(prefix="/credentials", tags=["Credentials Vault"])


class CredentialCreateSchema(BaseModel):
    project_id: UUID | str
    name: str = Field(..., min_length=2, max_length=120)
    credential_type: str = Field(..., pattern=r"^(username_password|api_token|bearer_token)$")
    username: str | None = None
    secret_value: str = Field(..., min_length=1)
    domain_scope: str | None = None


class CredentialUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    credential_type: str | None = Field(default=None, pattern=r"^(username_password|api_token|bearer_token)$")
    username: str | None = None
    secret_value: str | None = Field(default=None, min_length=1)  # Optional rotation
    domain_scope: str | None = None


def _format_credential_metadata(c: Credential) -> dict[str, Any]:
    """Safe metadata dictionary. The plaintext secret is NEVER exposed over the REST API."""
    return {
        "id": str(c.id),
        "project_id": str(c.project_id),
        "name": c.name,
        "credential_type": c.credential_type,
        "username": c.username,
        "domain_scope": c.domain_scope,
        "masked_secret": "••••••••",
        "is_encrypted": True,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def resolve_credential_for_execution(
    db: Session,
    credential_id: UUID,
    project_id: UUID,
    current_domain: str | None = None,
    user_id: UUID | None = None,
) -> dict[str, str]:
    """Securely resolves and decrypts an AES-256 secret for in-memory browser automation injection.

    Enforces project isolation, domain scope restriction, and audit trail generation.
    Raw secrets are injected strictly in-memory into the browser session and never saved to logs.
    """
    cred = db.query(Credential).filter(Credential.id == credential_id).first()
    if not cred:
        raise ValueError(f"Credential {credential_id} not found")
    if cred.project_id != project_id:
        raise PermissionError(f"Credential {credential_id} does not belong to project {project_id}")

    # Enforce domain scope limitation (e.g. *.company.internal or login.internal.net)
    if cred.domain_scope and current_domain:
        norm_scope = cred.domain_scope.lower().strip()
        norm_dom = current_domain.lower().strip()
        if not fnmatch.fnmatch(norm_dom, norm_scope):
            raise PermissionError(
                f"Security Violation: Credential '{cred.name}' is restricted to domain scope '{cred.domain_scope}', "
                f"refusing injection into '{current_domain}'"
            )

    decrypted_secret = SecretManager.decrypt(cred.secret_encrypted)

    log_audit_event(
        db=db,
        user_id=user_id,
        action="credential.injected",
        resource_type="credential",
        resource_id=str(cred.id),
        details={"name": cred.name, "domain": current_domain, "project_id": str(project_id)},
    )

    return {
        "username": cred.username or "",
        "secret": decrypted_secret,
        "type": cred.credential_type,
    }


@router.get("", response_model=list[dict[str, Any]])
def list_credentials(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("credentials:read", "credentials:manage")),
) -> list[dict[str, Any]]:
    """List stored credentials metadata. Raw secrets are NEVER returned."""
    query = db.query(Credential)

    if not current_user.is_superuser:
        user_projects = (
            db.query(Project.id)
            .filter(
                (Project.owner_id == current_user.id)
                | (Project.members.any(ProjectMember.user_id == current_user.id))
            )
            .subquery()
        )
        query = query.filter(Credential.project_id.in_(user_projects))

    if project_id:
        proj = resolve_project_id(db, project_id, current_user.id, is_superuser=current_user.is_superuser)
        if proj:
            query = query.filter(Credential.project_id == proj.id)
        else:
            return []

    creds = query.order_by(Credential.created_at.desc()).all()
    return [_format_credential_metadata(c) for c in creds]


@router.get("/{credential_id}", response_model=dict[str, Any])
def get_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("credentials:read", "credentials:manage")),
) -> dict[str, Any]:
    """Retrieve metadata for a specific credential with project access verification."""
    cred = db.query(Credential).filter(Credential.id == credential_id).first()
    if not cred or not user_has_project_access(db, cred.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    return _format_credential_metadata(cred)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_credential(
    payload: CredentialCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("credentials:manage")),
) -> dict[str, Any]:
    """Store encrypted credential. Secret is write-only AES-256-GCM encrypted."""
    project = resolve_project_id(db, payload.project_id, current_user.id, is_superuser=current_user.is_superuser)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target project not found")

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
        action="credential.created",
        resource_type="credential",
        resource_id=str(new_cred.id),
        details={"name": new_cred.name, "type": new_cred.credential_type, "project_id": str(project.id)},
    )

    return _format_credential_metadata(new_cred)


@router.put("/{credential_id}")
def update_credential(
    credential_id: UUID,
    payload: CredentialUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("credentials:manage")),
) -> dict[str, Any]:
    """Update credential metadata or rotate secret value with AES-256 encryption."""
    cred = db.query(Credential).filter(Credential.id == credential_id).first()
    if not cred or not user_has_project_access(db, cred.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    if payload.name is not None:
        cred.name = payload.name.strip()
    if payload.credential_type is not None:
        cred.credential_type = payload.credential_type
    if payload.username is not None:
        cred.username = payload.username.strip() if payload.username else None
    if payload.domain_scope is not None:
        cred.domain_scope = payload.domain_scope.strip() if payload.domain_scope else None
    if payload.secret_value is not None:
        cred.secret_encrypted = SecretManager.encrypt(payload.secret_value)

    db.commit()
    db.refresh(cred)

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="credential.updated",
        resource_type="credential",
        resource_id=str(cred.id),
        details={"name": cred.name, "secret_rotated": payload.secret_value is not None},
    )

    return _format_credential_metadata(cred)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(
    credential_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("credentials:manage")),
) -> None:
    """Permanently revoke and delete a credential."""
    cred = db.query(Credential).filter(Credential.id == credential_id).first()
    if not cred or not user_has_project_access(db, cred.project_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    cred_id_str = str(cred.id)
    cred_name = cred.name
    db.delete(cred)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        action="credential.deleted",
        resource_type="credential",
        resource_id=cred_id_str,
        details={"name": cred_name},
    )
