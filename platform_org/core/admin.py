from django.contrib import admin
from .models import (
    MicroEnterprise, MEOwner, SLATemplate, MEContract, VAMAgreement, MEKPI,
    MicroEnterpriseType, MicroEnterpriseStatus, MEService, ContractService, ContractStatus,
    ServiceSLACost
)

@admin.register(ServiceSLACost)
class ServiceSLACostAdmin(admin.ModelAdmin):
    list_display = ("service", "sla_template", "cost", "tenant")
    list_filter = ("tenant", "service")

@admin.register(ContractStatus)
class ContractStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "code")

@admin.register(MEService)
class MEServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "provider_me", "cost", "sla_template", "tenant")
    list_filter = ("tenant", "provider_me", "parent")
    search_fields = ("name", "provider_me__name")
    inlines = [type("ServiceSLACostInline", (admin.TabularInline,), {"model": ServiceSLACost, "extra": 1})]

@admin.register(MicroEnterpriseType)
class MicroEnterpriseTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "code")

@admin.register(MicroEnterpriseStatus)
class MicroEnterpriseStatusAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "code")

@admin.register(MicroEnterprise)
class MicroEnterpriseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "me_type", "status", "tenant")
    list_filter = ("tenant", "me_type", "status")
    search_fields = ("code", "name")

@admin.register(MEOwner)
class MEOwnerAdmin(admin.ModelAdmin):
    list_display = ("me", "user", "role_in_me", "is_primary", "tenant")
    list_filter = ("tenant", "is_primary")
    search_fields = ("me__name", "user__username")

@admin.register(SLATemplate)
class SLATemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "response_time_hours", "resolution_time_hours", "availability_percent", "tenant")
    list_filter = ("tenant",)
    search_fields = ("name",)

class ContractServiceInline(admin.TabularInline):
    model = ContractService
    fields = ("service", "billing_type", "quantity", "period_start", "period_end", "sla_template")
    extra = 1

@admin.register(MEContract)
class MEContractAdmin(admin.ModelAdmin):
    list_display = ("code", "provider_me", "consumer_me", "status", "start_date", "end_date", "contract_value", "tenant")
    list_filter = ("tenant", "status")
    search_fields = ("code", "provider_me__name", "consumer_me__name")
    inlines = [ContractServiceInline]

@admin.register(ContractService)
class ContractServiceAdmin(admin.ModelAdmin):
    list_display = ("contract", "service", "billing_type", "quantity", "sla_template", "tenant")
    list_filter = ("tenant", "billing_type")

@admin.register(VAMAgreement)
class VAMAgreementAdmin(admin.ModelAdmin):
    list_display = ("code", "me", "total_committed_amount", "tenant")
    list_filter = ("tenant",)
    search_fields = ("code", "me__name")

@admin.register(MEKPI)
class MEKPIAdmin(admin.ModelAdmin):
    list_display = ("code", "me", "name", "target_value", "actual_value", "tenant")
    list_filter = ("tenant", "me")
    search_fields = ("code", "name", "me__name")
