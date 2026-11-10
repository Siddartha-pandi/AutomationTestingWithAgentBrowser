"""Project, Environment, and Credential database models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.app.db.session import Base


class Project(Base):
    """Top-level organizational tenant isolating flows, tests, and environments."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(160), index=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", back_populates="projects")
    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")
    credentials = relationship("Credential", back_populates="project", cascade="all, delete-orphan")
    definitions = relationship("AutomationDefinition", back_populates="project", cascade="all, delete-orphan")
    element_profiles = relationship("ElementProfile", back_populates="project", cascade="all, delete-orphan")
    executions = relationship("Execution", back_populates="project", cascade="all, delete-orphan")


class Environment(Base):
    """Target execution environment with domain restriction rules and encrypted variables."""

    __tablename__ = "environments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(80), index=True, nullable=False)  # Production, Staging, QA, Local
    base_url = Column(String(512), nullable=False)
    allowed_domains = Column(JSONB, default=list, nullable=False)  # Security domain restriction list
    variables_encrypted = Column(Text, nullable=True)  # AES-256 encrypted variables dictionary
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="environments")
    schedules = relationship("Schedule", back_populates="environment")


class Credential(Base):
    """Encrypted credential vault storing secrets for automated browser workflows."""

    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String(120), index=True, nullable=False)
    credential_type = Column(String(32), nullable=False)  # username_password, api_token, bearer_token
    username = Column(String(256), nullable=True)
    secret_encrypted = Column(Text, nullable=False)  # AES-256 encrypted secret
    domain_scope = Column(String(256), nullable=True)  # Domain limitation (e.g. *.mycompany.com)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), server_default=func.now(), nullable=False)

    project = relationship("Project", back_populates="credentials")

