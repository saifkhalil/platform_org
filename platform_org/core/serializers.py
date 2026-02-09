from rest_framework import serializers
from .models import (
    MicroEnterprise, SLATemplate, MEContract, VAMAgreement, MEKPI, 
    MicroEnterpriseType, MicroEnterpriseStatus, MEService, ContractService,
    ServiceSLACost
)

class BaseTenantSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "tenant" in self.fields:
            self.fields["tenant"].read_only = True

class MicroEnterpriseTypeSerializer(BaseTenantSerializer):
    class Meta:
        model = MicroEnterpriseType
        fields = "__all__"

class MicroEnterpriseStatusSerializer(BaseTenantSerializer):
    class Meta:
        model = MicroEnterpriseStatus
        fields = "__all__"

class MicroEnterpriseSerializer(BaseTenantSerializer):
    me_type_name = serializers.CharField(source="me_type.name", read_only=True)
    status_name = serializers.CharField(source="status.name", read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = MicroEnterprise
        fields = "__all__"

    def get_services(self, obj):
        # Return only top-level services for this ME, they will include sub_services via MEServiceSerializer
        services = obj.services.filter(parent__isnull=True)
        return MEServiceSerializer(services, many=True).data

class SLATemplateSerializer(BaseTenantSerializer):
    class Meta:
        model = SLATemplate
        fields = "__all__"

class ServiceSLACostSerializer(BaseTenantSerializer):
    class Meta:
        model = ServiceSLACost
        fields = ["sla_template", "cost"]

class MEServiceSerializer(BaseTenantSerializer):
    provider_me_name = serializers.CharField(source="provider_me.name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    sub_services = serializers.SerializerMethodField()
    sla_costs = ServiceSLACostSerializer(many=True, read_only=True)

    class Meta:
        model = MEService
        fields = "__all__"

    def get_sub_services(self, obj):
        if obj.sub_services.exists():
            return MEServiceSerializer(obj.sub_services.all(), many=True).data
        return []

class ContractServiceSerializer(BaseTenantSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    sla_template_name = serializers.CharField(source="sla_template.name", read_only=True)
    cost = serializers.DecimalField(source="service.cost", max_digits=18, decimal_places=2, read_only=True)
    class Meta:
        model = ContractService
        fields = [
            'id', 'tenant', 'contract', 'service', 'service_name', 
            'billing_type', 'quantity', 'period_start', 'period_end', 
            'sla_template', 'sla_template_name', 'cost', 'created_at', 'updated_at'
        ]

class MEContractSerializer(BaseTenantSerializer):
    contract_services = ContractServiceSerializer(many=True, read_only=True)
    provider_me_name = serializers.CharField(source="provider_me.name", read_only=True)
    consumer_me_name = serializers.CharField(source="consumer_me.name", read_only=True)
    class Meta:
        model = MEContract
        fields = "__all__"

class VAMAgreementSerializer(BaseTenantSerializer):
    class Meta:
        model = VAMAgreement
        fields = "__all__"

class MEKPISerializer(BaseTenantSerializer):
    class Meta:
        model = MEKPI
        fields = "__all__"
