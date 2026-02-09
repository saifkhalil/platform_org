from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import MicroEnterprise, SLATemplate, MEContract, VAMAgreement, MEKPI, MEOwner, MicroEnterpriseType, MicroEnterpriseStatus, MEService
from .serializers import (
    MicroEnterpriseSerializer, SLATemplateSerializer, MEContractSerializer, 
    VAMAgreementSerializer, MEKPISerializer, MicroEnterpriseTypeSerializer, 
    MicroEnterpriseStatusSerializer, MEServiceSerializer
)
from .permissions import RowLevelMEPermission, IsPlatformAdmin, is_platform_admin
from .audit import log_event
from platform_org.integrations.tasks import noop_integration_event

def owned_me_ids(user):
    return list(MEOwner.objects.filter(user=user).values_list("me_id", flat=True))

class MicroEnterpriseViewSet(viewsets.ModelViewSet):
    serializer_class = MicroEnterpriseSerializer
    permission_classes = [IsAuthenticated, RowLevelMEPermission]
    def get_queryset(self):
        qs = MicroEnterprise.objects.filter(tenant=self.request.tenant).order_by("-created_at")
        return qs if is_platform_admin(self.request.user) else qs.filter(id__in=owned_me_ids(self.request.user))
    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.tenant)
        log_event(actor=self.request.user, action="CREATE", entity=obj, summary="Created ME")
    def perform_update(self, serializer):
        obj = serializer.save()
        log_event(actor=self.request.user, action="UPDATE", entity=obj, summary="Updated ME")

class MicroEnterpriseTypeViewSet(viewsets.ModelViewSet):
    serializer_class = MicroEnterpriseTypeSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return MicroEnterpriseType.objects.filter(tenant=self.request.tenant).order_by("name")
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class MicroEnterpriseStatusViewSet(viewsets.ModelViewSet):
    serializer_class = MicroEnterpriseStatusSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return MicroEnterpriseStatus.objects.filter(tenant=self.request.tenant).order_by("name")
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class MEServiceViewSet(viewsets.ModelViewSet):
    serializer_class = MEServiceSerializer
    permission_classes = [IsAuthenticated, RowLevelMEPermission]
    def get_queryset(self):
        qs = MEService.objects.filter(tenant=self.request.tenant).select_related("provider_me").all().order_by("name")
        if is_platform_admin(self.request.user): return qs
        return qs.filter(provider_me_id__in=owned_me_ids(self.request.user))
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class SLATemplateViewSet(viewsets.ModelViewSet):
    serializer_class = SLATemplateSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    def get_queryset(self):
        return SLATemplate.objects.filter(tenant=self.request.tenant).order_by("name")
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class MEContractViewSet(viewsets.ModelViewSet):
    serializer_class = MEContractSerializer
    permission_classes = [IsAuthenticated, RowLevelMEPermission]
    def get_queryset(self):
        qs = MEContract.objects.filter(tenant=self.request.tenant).select_related("provider_me","consumer_me").all().order_by("-created_at")
        if is_platform_admin(self.request.user): return qs
        ids = owned_me_ids(self.request.user)
        return (qs.filter(provider_me_id__in=ids) | qs.filter(consumer_me_id__in=ids)).distinct()
    def perform_create(self, serializer):
        obj = serializer.save(tenant=self.request.tenant)
        log_event(actor=self.request.user, action="CREATE", entity=obj, summary="Created Contract")
    def perform_update(self, serializer):
        obj = serializer.save()
        log_event(actor=self.request.user, action="UPDATE", entity=obj, summary="Updated Contract")
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        contract = self.get_object()
        contract.status = "ACTIVE"
        contract.save(update_fields=["status","updated_at"])
        log_event(actor=request.user, action="STATE_CHANGE", entity=contract, summary="Contract activated")
        noop_integration_event.delay("contract_activated", {"code": contract.code})
        return Response({"status": contract.status})

class VAMAgreementViewSet(viewsets.ModelViewSet):
    serializer_class = VAMAgreementSerializer
    permission_classes = [IsAuthenticated, RowLevelMEPermission]
    def get_queryset(self):
        qs = VAMAgreement.objects.filter(tenant=self.request.tenant).select_related("me").all().order_by("-created_at")
        return qs if is_platform_admin(self.request.user) else qs.filter(me_id__in=owned_me_ids(self.request.user))
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class MEKPIViewSet(viewsets.ModelViewSet):
    serializer_class = MEKPISerializer
    permission_classes = [IsAuthenticated, RowLevelMEPermission]
    def get_queryset(self):
        qs = MEKPI.objects.filter(tenant=self.request.tenant).select_related("me").all().order_by("-created_at")
        return qs if is_platform_admin(self.request.user) else qs.filter(me_id__in=owned_me_ids(self.request.user))
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)
