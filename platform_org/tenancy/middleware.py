from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from .models import Tenant, TenantUser


class TenantMiddleware(MiddlewareMixin):
    """Resolve tenant from subdomain, header, Entra claims, or user mapping."""

    def process_request(self, request):
        tenant = None
        host = request.get_host().split(":")[0]
        subdomain = host.split(".")[0] if host and "." in host else None

        if subdomain and subdomain not in {"www", "localhost"}:
            tenant = Tenant.objects.filter(slug=subdomain, is_active=True).first()

        if not tenant:
            tenant_header = request.headers.get("X-Tenant")
            if tenant_header:
                tenant = Tenant.objects.filter(slug=tenant_header, is_active=True).first()

        claims = getattr(request, "entra_claims", None)
        if not tenant and claims:
            tid = claims.get("tid")
            groups = claims.get("groups") or []
            if tid:
                tenant = Tenant.objects.filter(entra_tenant_id=tid, is_active=True).first()
            if not tenant and groups:
                tenant = Tenant.objects.filter(entra_group_id__in=groups, is_active=True).first()

        if not tenant and request.user.is_authenticated:
            membership = TenantUser.objects.filter(user=request.user, is_active=True, tenant__is_active=True).first()
            if membership:
                tenant = membership.tenant

        if not tenant and getattr(settings, "DEBUG", False):
            tenant, _ = Tenant.objects.get_or_create(slug="default", defaults={"name": "Default Tenant"})

        request.tenant = tenant
