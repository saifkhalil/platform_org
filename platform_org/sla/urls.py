from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api import ServiceRequestViewSet, SLABreachViewSet

router = DefaultRouter()
router.register(r"sla/requests", ServiceRequestViewSet, basename="sla-requests")
router.register(r"sla/breaches", SLABreachViewSet, basename="sla-breaches")

urlpatterns = [
    path("api/", include(router.urls)),
]
