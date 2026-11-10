"""Binary artifact storage, SHA-256 integrity verification, and directory traversal protection.

Adheres strictly to Company Data Protection policies:
- All large binary files (screenshots, traces, DOM dumps) stored in approved private filesystem.
- Only metadata and cryptographic hashes indexed in PostgreSQL.
- Hardened against path traversal attacks.
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.execution import Artifact, DOMSnapshot
from backend.app.security.redaction import Redactor
from backend.config import settings

logger = logging.getLogger(__name__)


class ArtifactSecurityError(Exception):
    """Raised on unauthorized path traversal or storage integrity violations."""


class ArtifactManager:
    """Enterprise artifact manager for screenshots, DOM snapshots, and execution logs."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir or settings.storage_dir).resolve()
        self.screenshots_dir = self.storage_dir / "screenshots"
        self.dom_dir = self.storage_dir / "dom_snapshots"
        self.artifacts_dir = self.storage_dir / "artifacts"
        self.exports_dir = self.storage_dir / "exports"

        # Ensure directory structure exists
        for d in (self.screenshots_dir, self.dom_dir, self.artifacts_dir, self.exports_dir):
            d.mkdir(parents=True, exist_ok=True)

        self.redactor = Redactor()

    @staticmethod
    def calculate_sha256(file_path: Path | str) -> str:
        """Calculates cryptographic SHA-256 digest of a file using chunked streaming."""
        hasher = hashlib.sha256()
        p = Path(file_path)
        with p.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_safe_artifact_path(self, artifact: Artifact) -> Path:
        """Resolves artifact file path and strictly prevents directory traversal attacks."""
        resolved = Path(artifact.file_path).resolve()
        try:
            resolved.relative_to(self.storage_dir)
        except ValueError:
            raise ArtifactSecurityError(
                f"Path traversal detected: Artifact file {resolved} is outside approved storage directory {self.storage_dir}"
            )

        if not resolved.exists():
            raise FileNotFoundError(f"Artifact file not found on disk: {resolved}")

        return resolved

    def verify_artifact_integrity(self, artifact: Artifact) -> bool:
        """Verifies that on-disk artifact content matches the SHA-256 hash in PostgreSQL."""
        try:
            safe_path = self.get_safe_artifact_path(artifact)
            current_hash = self.calculate_sha256(safe_path)
            return current_hash.lower() == artifact.sha256_hash.lower()
        except Exception as err:
            logger.warning("Integrity check failed for artifact %s: %s", artifact.id, err)
            return False

    def save_file_artifact(
        self,
        db: Session,
        execution_id: UUID,
        artifact_type: str,
        content_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
    ) -> Artifact:
        """Stores binary bytes onto disk, computes SHA-256, and records metadata in PostgreSQL."""
        exec_sub_dir = self.artifacts_dir / str(execution_id)
        exec_sub_dir.mkdir(parents=True, exist_ok=True)

        clean_filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_", "."))
        target_path = exec_sub_dir / clean_filename

        with target_path.open("wb") as f:
            f.write(content_bytes)

        file_size = len(content_bytes)
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()

        if not mime_type:
            inferred, _ = mimetypes.guess_type(clean_filename)
            mime_type = inferred or "application/octet-stream"

        artifact = Artifact(
            execution_id=execution_id,
            artifact_type=artifact_type,
            file_path=str(target_path),
            file_size_bytes=file_size,
            mime_type=mime_type,
            sha256_hash=sha256_hash,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        logger.info(
            "Saved artifact %s (type=%s, size=%d bytes, sha256=%s)",
            artifact.id,
            artifact_type,
            file_size,
            sha256_hash[:8],
        )
        return artifact

    def save_screenshot_artifact(
        self,
        db: Session,
        execution_id: UUID,
        screenshot_path: Path | str,
    ) -> Artifact:
        """Indexes an existing screenshot into the Artifact database table."""
        path = Path(screenshot_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Screenshot file does not exist: {path}")

        file_size = path.stat().st_size
        sha256_hash = self.calculate_sha256(path)

        artifact = Artifact(
            execution_id=execution_id,
            artifact_type="screenshot",
            file_path=str(path),
            file_size_bytes=file_size,
            mime_type="image/png",
            sha256_hash=sha256_hash,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact

    def save_dom_snapshot_artifact(
        self,
        db: Session,
        execution_id: UUID,
        page_url: str,
        dom_data: dict[str, Any] | str,
    ) -> tuple[DOMSnapshot, Artifact]:
        """Saves redacted DOM snapshot into approved private storage and indexes both models."""
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"dom_{execution_id}_{timestamp_str}.json"
        target_path = self.dom_dir / filename

        # Redact DOM data
        if isinstance(dom_data, dict):
            redacted_data = self.redactor.redact_dict(dom_data)
            content_str = json.dumps(redacted_data, indent=2, default=str)
            element_count = int(redacted_data.get("total_elements", 0))
        else:
            content_str = self.redactor.redact_text(str(dom_data))
            element_count = content_str.count("<")

        content_bytes = content_str.encode("utf-8")
        with target_path.open("wb") as f:
            f.write(content_bytes)

        file_size = len(content_bytes)
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()

        # 1. Create DOMSnapshot record
        dom_snapshot = DOMSnapshot(
            execution_id=execution_id,
            page_url=page_url,
            snapshot_path=str(target_path),
            element_count=element_count,
        )
        db.add(dom_snapshot)

        # 2. Create Artifact record
        artifact = Artifact(
            execution_id=execution_id,
            artifact_type="dom",
            file_path=str(target_path),
            file_size_bytes=file_size,
            mime_type="application/json",
            sha256_hash=sha256_hash,
        )
        db.add(artifact)
        db.commit()
        db.refresh(dom_snapshot)
        db.refresh(artifact)

        return dom_snapshot, artifact

