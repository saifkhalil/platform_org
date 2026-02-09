from platform_org.audit.models import AuditEvent
def log_event(*, actor, action: str, entity, summary: str = "", payload: dict | None = None):
    AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=str(getattr(entity, "pk", "")),
        summary=summary[:255],
        payload=payload or {},
    )
