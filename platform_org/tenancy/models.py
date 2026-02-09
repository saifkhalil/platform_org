from django.conf import settings
from django.db import models
from django.utils import timezone

class Tenant(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    entra_tenant_id = models.CharField(max_length=64, blank=True, db_index=True)
    entra_group_id = models.CharField(max_length=64, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

class TenantUser(models.Model):
    class Role(models.TextChoices):
        PLATFORM_ADMIN = "PLATFORM_ADMIN", "Platform Admin"
        TENANT_ADMIN = "TENANT_ADMIN", "Tenant Admin"
        MEMBER = "MEMBER", "Member"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tenant_users")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        unique_together = [("tenant", "user")]
