from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include(("platform_org.urls", "platform_org"), namespace="platform_org")),
    path("", include("platform_org.sla.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/auth/", include("platform_org.accounts.urls")),
    path("api/", include("platform_org.core.urls")),
    path("", include("platform_org.health.urls")),
]
