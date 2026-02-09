from rest_framework import serializers, viewsets, permissions
from .models import ServiceRequest, SLABreachEvent

class TenantScopedMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, "tenant", None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()

class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = ["tenant"]

class SLABreachSerializer(serializers.ModelSerializer):
    request_title = serializers.CharField(source="request.title", read_only=True)
    class Meta:
        model = SLABreachEvent
        fields = ["id","tenant","request","request_title","breach_type","breach_at","details"]
        read_only_fields = ["tenant"]

class ServiceRequestViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = ServiceRequest.objects.select_related("contract","tenant").all()

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class SLABreachViewSet(TenantScopedMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SLABreachSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = SLABreachEvent.objects.select_related("request","tenant").order_by("-breach_at")
