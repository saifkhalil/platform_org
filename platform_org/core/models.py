from django.conf import settings
from django.db import models
from django.utils import timezone
from platform_org.tenancy.models import Tenant
from .audit import log_event

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class MicroEnterpriseType(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_types")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return self.name

class MicroEnterpriseStatus(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_statuses")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)

    class Meta:
        unique_together = [("tenant", "code")]
        verbose_name_plural = "Micro enterprise statuses"

    def __str__(self):
        return self.name

class ContractStatus(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="contract_statuses")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)

    class Meta:
        unique_together = [("tenant", "code")]
        verbose_name_plural = "Contract statuses"

    def __str__(self):
        return self.name

class MicroEnterprise(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="micro_enterprises")
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    me_type = models.ForeignKey(MicroEnterpriseType, on_delete=models.PROTECT, null=True, blank=True, related_name="micro_enterprises")
    status = models.ForeignKey(MicroEnterpriseStatus, on_delete=models.PROTECT, null=True, blank=True, related_name="micro_enterprises")
    autonomy_level = models.CharField(max_length=20, default="RESTRICTED")
    value_proposition = models.TextField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    cost_center = models.CharField(max_length=100, blank=True)
    owners = models.ManyToManyField(settings.AUTH_USER_MODEL, through="MEOwner", related_name="micro_enterprises")

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return self.name

class MEOwner(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_owners")
    me = models.ForeignKey(MicroEnterprise, on_delete=models.CASCADE, related_name="owner_links")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role_in_me = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    class Meta:
        unique_together = [("me","user")]

class SLATemplate(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="sla_templates")
    name = models.CharField(max_length=255)  # Removed unique=True as it should be unique per tenant
    response_time_hours = models.PositiveIntegerField(null=True, blank=True)
    resolution_time_hours = models.PositiveIntegerField(null=True, blank=True)
    availability_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("tenant", "name")]

    def __str__(self):
        return self.name

class MEService(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_services")
    provider_me = models.ForeignKey(MicroEnterprise, on_delete=models.CASCADE, related_name="services")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name="sub_services")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    sla_template = models.ForeignKey(SLATemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="services")

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} -> {self.name} ({self.provider_me.name})"
        return f"{self.name} ({self.provider_me.name})"

class ServiceSLACost(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="service_sla_costs")
    service = models.ForeignKey(MEService, on_delete=models.CASCADE, related_name="sla_costs")
    sla_template = models.ForeignKey(SLATemplate, on_delete=models.CASCADE, related_name="service_costs")
    cost = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        unique_together = [("service", "sla_template")]

    def __str__(self):
        return f"{self.service.name} - {self.sla_template.name}: {self.cost}"

class MEContract(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_contracts")
    code = models.CharField(max_length=50)
    provider_me = models.ForeignKey(MicroEnterprise, on_delete=models.PROTECT, related_name="provided_contracts")
    consumer_me = models.ForeignKey(MicroEnterprise, on_delete=models.PROTECT, related_name="consumed_contracts")
    services = models.ManyToManyField(MEService, through="ContractService", related_name="contracts")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    contract_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default="DRAFT")

    # Kept for backward compatibility or as a primary SLA if needed, 
    # but the request implies per-service SLA.
    sla_template = models.ForeignKey(SLATemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name="contracts")

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.code} ({self.provider_me.name} -> {self.consumer_me.name})"

class ContractService(TimeStampedModel):
    BILLING_TYPES = [
        ('QUANTITY', 'Quantity'),
        ('PERIOD', 'Period'),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="contract_services")
    contract = models.ForeignKey(MEContract, on_delete=models.CASCADE, related_name="contract_services")
    service = models.ForeignKey(MEService, on_delete=models.PROTECT, related_name="contract_links")
    billing_type = models.CharField(max_length=20, choices=BILLING_TYPES, default='PERIOD')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    sla_template = models.ForeignKey(SLATemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.contract.code} - {self.service.name}"

class VAMAgreement(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="vam_agreements")
    code = models.CharField(max_length=50)
    me = models.ForeignKey(MicroEnterprise, on_delete=models.PROTECT, related_name="vam_agreements")
    total_committed_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        unique_together = [("tenant", "code")]

class MEKPI(TimeStampedModel):
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="me_kpis")
    code = models.CharField(max_length=50)
    me = models.ForeignKey(MicroEnterprise, on_delete=models.PROTECT, related_name="kpis")
    name = models.CharField(max_length=255)
    target_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    actual_value = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [("tenant", "code")]

    def delete(self, *args, **kwargs):
        log_event(actor=None, action="DELETE", entity=self, summary=f"Deleted {self.__class__.__name__}")
        super().delete(*args, **kwargs)
