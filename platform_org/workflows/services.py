from django.db import transaction

from platform_org.core.notifications import send_alert_email
from platform_org.workflows.models import WorkflowDefinition, WorkflowTransition, WorkflowStateAction


def get_active_workflow(tenant, entity_type):
    return WorkflowDefinition.objects.filter(tenant=tenant, entity_type=entity_type, is_active=True).first()


def get_initial_state_code(tenant, entity_type, default_code):
    workflow = get_active_workflow(tenant, entity_type)
    if not workflow:
        return default_code
    initial = workflow.states.filter(is_initial=True).order_by("order").first()
    return initial.code if initial else default_code


def get_state_choices(tenant, entity_type):
    workflow = get_active_workflow(tenant, entity_type)
    if not workflow:
        return []
    return list(workflow.states.values_list("code", "name"))


def can_transition(tenant, entity_type, current_state, target_state):
    workflow = get_active_workflow(tenant, entity_type)
    if not workflow:
        return True
    if current_state == target_state:
        return True
    return WorkflowTransition.objects.filter(
        tenant=tenant,
        workflow=workflow,
        from_state__code=current_state,
        to_state__code=target_state,
    ).exists()


def build_mermaid(workflow):
    lines = ["flowchart LR"]
    transitions = workflow.transitions.select_related("from_state", "to_state").all()
    for t in transitions:
        lines.append(f"    {t.from_state.code} -->|{t.name}| {t.to_state.code}")
    if len(lines) == 1:
        lines.append("    EMPTY[No transitions configured]")
    return "\n".join(lines)


def execute_state_actions(instance, tenant, entity_type, target_state):
    workflow = get_active_workflow(tenant, entity_type)
    if not workflow:
        return
    actions = WorkflowStateAction.objects.filter(
        tenant=tenant,
        workflow=workflow,
        state__code=target_state,
        is_active=True,
    )
    with transaction.atomic():
        for action in actions:
            cfg = action.config or {}
            if action.action_type == WorkflowStateAction.ActionType.SEND_EMAIL:
                send_alert_email(
                    subject=cfg.get("subject", f"Workflow action: {action.name}"),
                    message=cfg.get("message", f"State changed to {target_state}"),
                    to_emails=cfg.get("to_emails", []),
                )
            elif action.action_type == WorkflowStateAction.ActionType.UPDATE_FIELD:
                field_name = cfg.get("field")
                value = cfg.get("value")
                if field_name and hasattr(instance, field_name):
                    setattr(instance, field_name, value)
                    update_fields = [field_name]
                    if hasattr(instance, "updated_at"):
                        update_fields.append("updated_at")
                    instance.save(update_fields=update_fields)
