from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    MicroEnterpriseViewSet, SLATemplateViewSet, MEContractViewSet, 
    VAMAgreementViewSet, MEKPIViewSet, MicroEnterpriseTypeViewSet, 
    MicroEnterpriseStatusViewSet, MEServiceViewSet
)
router = DefaultRouter()
router.register("micro-enterprises", MicroEnterpriseViewSet, basename="micro-enterprises")
router.register("me-types", MicroEnterpriseTypeViewSet, basename="me-types")
router.register("me-statuses", MicroEnterpriseStatusViewSet, basename="me-statuses")
router.register("me-services", MEServiceViewSet, basename="me-services")
router.register("sla-templates", SLATemplateViewSet, basename="sla-templates")
router.register("contracts", MEContractViewSet, basename="contracts")
router.register("vam-agreements", VAMAgreementViewSet, basename="vam-agreements")
router.register("kpis", MEKPIViewSet, basename="kpis")
urlpatterns = [path("", include(router.urls))]
