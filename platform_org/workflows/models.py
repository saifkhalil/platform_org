from django.db import models

from platform_org.tenancy.models import Tenant


class WorkflowDefinition(models.Model):
    class EntityType(models.TextChoices):
        CONTRACT = "CONTRACT", "Contract"
        REQUEST = "REQUEST", "Service Request"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="workflow_definitions")
    name = models.CharField(max_length=120)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("tenant", "name", "entity_type")]

    def __str__(self):
        return f"{self.tenant} - {self.name} ({self.entity_type})"


class WorkflowState(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="workflow_states")
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name="states")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=1)
    is_initial = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)

    class Meta:
        unique_together = [("workflow", "code")]
        ordering = ["workflow", "order", "name"]


class WorkflowTransition(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="workflow_transitions")
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name="outgoing")
    to_state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name="incoming")
    name = models.CharField(max_length=120)

    class Meta:
        unique_together = [("workflow", "from_state", "to_state")]


class WorkflowStateAction(models.Model):
    class ActionType(models.TextChoices):
        SEND_EMAIL = "SEND_EMAIL", "Send Email"
        UPDATE_FIELD = "UPDATE_FIELD", "Update Model Field"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="workflow_state_actions")
    workflow = models.ForeignKey(WorkflowDefinition, on_delete=models.CASCADE, related_name="actions")
    state = models.ForeignKey(WorkflowState, on_delete=models.CASCADE, related_name="actions")
    name = models.CharField(max_length=120)
    action_type = models.CharField(max_length=30, choices=ActionType.choices)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("workflow", "state", "name")]
