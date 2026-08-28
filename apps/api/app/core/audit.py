"""A minimal audit-event writer.

Callers must pass identifiers and operational metadata only. Never add
passwords, tokens, raw medical content, or other PHI payloads here.
"""

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record_audit_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    request_id: str,
    actor_user_id: str | None = None,
    subject_user_id: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Stage an append-only audit event in the current transaction."""
    db.add(
        AuditEvent(
            action=action,
            resource_type=resource_type,
            request_id=request_id,
            actor_user_id=actor_user_id,
            subject_user_id=subject_user_id,
            resource_id=resource_id,
            metadata_json=metadata or {},
        )
    )
