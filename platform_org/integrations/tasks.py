from celery import shared_task
@shared_task
def noop_integration_event(kind: str, payload: dict):
    return {"ok": True, "kind": kind, "payload": payload}
