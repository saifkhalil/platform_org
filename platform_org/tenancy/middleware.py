from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from .models import Tenant

class TenantMiddleware(MiddlewareMixin):
    """Resolve tenant in production from Entra claims (tid/groups) and mapping in DB.
    Dev fallback: X-Tenant header.
    """

    def process_request(self, request):
        tenant = None

        claims = getattr(request, "entra_claims", None)
        if claims:
            tid = claims.get("tid")
            groups = claims.get("groups") or []
            if tid:
                tenant = Tenant.objects.filter(entra_tenant_id=tid, is_active=True).first()
            if not tenant and groups:
                tenant = Tenant.objects.filter(entra_group_id__in=groups, is_active=True).first()

        if not tenant and getattr(settings, "DEBUG", False):
            code = request.headers.get("X-Tenant") or "default"
            tenant = Tenant.objects.filter(code=code, is_active=True).first()
            if not tenant and code == "default":
                tenant, _ = Tenant.objects.get_or_create(code="default", defaults={"name": "Default Tenant"})

        request.tenant = tenant
