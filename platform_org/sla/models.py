from django.db import models
from django.utils import timezone
from platform_org.tenancy.models import Tenant
from platform_org.core.models import MEContract

class ServiceRequest(models.Model):
    class Source(models.TextChoices):
        JITBIT = "JITBIT", "Jitbit"
        JIRA = "JIRA", "Jira"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="service_requests")
    contract = models.ForeignKey(MEContract, on_delete=models.PROTECT, related_name="service_requests")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=255)
    priority = models.CharField(max_length=30, default="MEDIUM")

    opened_at = models.DateTimeField(default=timezone.now)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

class SLABreachEvent(models.Model):
    class BreachType(models.TextChoices):
        RESPONSE = "RESPONSE", "Response Time"
        RESOLUTION = "RESOLUTION", "Resolution Time"

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="sla_breaches")
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="breaches")
    breach_type = models.CharField(max_length=20, choices=BreachType.choices)
    breach_at = models.DateTimeField(default=timezone.now)
    details = models.JSONField(default=dict, blank=True)
