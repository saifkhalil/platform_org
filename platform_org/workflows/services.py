from platform_org.workflows.models import WorkflowDefinition, WorkflowState, WorkflowTransition


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
