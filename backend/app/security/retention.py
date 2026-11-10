"""Artifact retention and scheduled purging for company data protection."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.models.execution import Artifact, DOMSnapshot, ExecutionLog

logger = logging.getLogger(__name__)

# Default retention horizons (days)
LOG_RETENTION_DAYS = 90
SCREENSHOT_RETENTION_DAYS = 30
DOM_SNAPSHOT_RETENTION_DAYS = 14


def purge_expired_artifacts(
    db: Session,
    log_days: int = LOG_RETENTION_DAYS,
    screenshot_days: int = SCREENSHOT_RETENTION_DAYS,
    dom_days: int = DOM_SNAPSHOT_RETENTION_DAYS,
) -> dict[str, int]:
    """Purges expired logs, screenshots, and DOM dumps per enterprise retention policy."""
    now = datetime.now(timezone.utc)
    purged_counts = {"logs": 0, "artifacts": 0, "dom_snapshots": 0}

    # 1. Purge expired logs
    log_cutoff = now - timedelta(days=log_days)
    log_del = db.query(ExecutionLog).filter(ExecutionLog.timestamp < log_cutoff).delete()
    purged_counts["logs"] = log_del

    # 2. Purge expired artifacts (and their files)
    artifact_cutoff = now - timedelta(days=screenshot_days)
    expired_artifacts = db.query(Artifact).filter(Artifact.created_at < artifact_cutoff).all()
    for art in expired_artifacts:
        file_path = Path(art.file_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError as err:
                logger.warning("Failed to delete expired artifact file %s: %s", file_path, err)
        db.delete(art)
    purged_counts["artifacts"] = len(expired_artifacts)

    # 3. Purge expired DOM snapshots
    dom_cutoff = now - timedelta(days=dom_days)
    expired_doms = db.query(DOMSnapshot).filter(DOMSnapshot.created_at < dom_cutoff).all()
    for dom in expired_doms:
        snap_path = Path(dom.snapshot_path)
        if snap_path.exists():
            try:
                snap_path.unlink()
            except OSError as err:
                logger.warning("Failed to delete expired DOM snapshot %s: %s", snap_path, err)
        db.delete(dom)
    purged_counts["dom_snapshots"] = len(expired_doms)

    db.commit()
    logger.info("Retention purge completed: %s", purged_counts)
    return purged_counts

