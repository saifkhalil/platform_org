from django.contrib import admin
from .models import ServiceRequest, SLABreachEvent

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "external_id", "source", "status", "contract", "opened_at", "tenant")
    list_filter = ("tenant", "status", "source")
    search_fields = ("title", "external_id")

@admin.register(SLABreachEvent)
class SLABreachEventAdmin(admin.ModelAdmin):
    list_display = ("request", "breach_type", "breach_at", "tenant")
    list_filter = ("tenant", "breach_type")
    search_fields = ("request__title",)
