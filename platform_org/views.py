from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import redirect

from .tenancy.models import Tenant, TenantUser
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from .core.models import (
    MicroEnterprise, MEContract, VAMAgreement, MEKPI, 
    MicroEnterpriseType, MicroEnterpriseStatus, MEService, 
    ContractService, MEOwner
)
from .sla.models import ServiceRequest, SLABreachEvent
from .workflows.models import WorkflowDefinition, WorkflowState, WorkflowTransition, WorkflowStateAction
from .workflows.services import get_active_workflow, get_initial_state_code, get_state_choices, can_transition, execute_state_actions, build_mermaid




def get_user_consumer_me(user, tenant):
    if not user or not user.is_authenticated or not tenant:
        return None
    primary = MEOwner.objects.filter(tenant=tenant, user=user, is_primary=True).select_related("me").first()
    if primary:
        return primary.me
    link = MEOwner.objects.filter(tenant=tenant, user=user).select_related("me").first()
    return link.me if link else None


def has_write_access(user, tenant):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or user.groups.filter(name="Platform Admin").exists():
        return True
    if not tenant:
        return False
    return TenantUser.objects.filter(
        user=user,
        tenant=tenant,
        is_active=True,
        role__in=[
            TenantUser.Role.PLATFORM_ADMIN,
            TenantUser.Role.ME_LEAD,
            TenantUser.Role.FINANCE,
        ],
    ).exists()

class TenantScopedMixin:
    """Scopes queryset to request.tenant when available and enforces write permissions."""

    paginate_by = 20

    def get_tenant(self):
        return getattr(self.request, "tenant", None)

    def scope_queryset(self, qs):
        tenant = self.get_tenant()
        if tenant:
            return qs.filter(tenant=tenant)
        return qs

    def dispatch(self, request, *args, **kwargs):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not has_write_access(request.user, self.get_tenant()):
            raise PermissionDenied("You do not have permission to modify tenant data.")
        return super().dispatch(request, *args, **kwargs)


class TenantAssignMixin:
    """Assigns request.tenant on create."""

    def form_valid(self, form):
        tenant = getattr(self.request, "tenant", None)
        if tenant and hasattr(form.instance, "tenant_id") and not form.instance.tenant_id:
            form.instance.tenant = tenant
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class DashboardView(TenantScopedMixin, TemplateView):
    template_name = "platform_org/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.get_tenant()

        ctx["tenant"] = tenant
        ctx["me_count"] = self.scope_queryset(MicroEnterprise.objects.all()).count()
        ctx["service_count"] = self.scope_queryset(MEService.objects.all()).count()
        ctx["contract_count"] = self.scope_queryset(MEContract.objects.all()).count()
        ctx["vam_count"] = self.scope_queryset(VAMAgreement.objects.all()).count()
        ctx["kpi_count"] = self.scope_queryset(MEKPI.objects.all()).count()
        ctx["request_count"] = self.scope_queryset(ServiceRequest.objects.all()).count()
        ctx["breach_count"] = self.scope_queryset(SLABreachEvent.objects.all()).count()
        return ctx


# -------------------------
# MicroEnterprise
# -------------------------
@method_decorator(login_required, name="dispatch")
class MicroEnterpriseListView(TenantScopedMixin, ListView):
    model = MicroEnterprise
    context_object_name = "items"
    template_name = "platform_org/micro_enterprise_list.html"

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("tenant", "me_type", "status"))
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        me_type = self.request.GET.get("me_type")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        if status:
            qs = qs.filter(status_id=status)
        if me_type:
            qs = qs.filter(me_type_id=me_type)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        if tenant:
            context["statuses"] = MicroEnterpriseStatus.objects.filter(tenant=tenant)
            context["types"] = MicroEnterpriseType.objects.filter(tenant=tenant)
        return context


@method_decorator(login_required, name="dispatch")
class MicroEnterpriseCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = MicroEnterprise
    fields = ["code", "name", "me_type", "status", "department", "cost_center"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:micro_enterprise_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me_type"].queryset = MicroEnterpriseType.objects.filter(tenant=tenant)
            form.fields["status"].queryset = MicroEnterpriseStatus.objects.filter(tenant=tenant)
        return form


@method_decorator(login_required, name="dispatch")
class MicroEnterpriseUpdateView(TenantScopedMixin, UpdateView):
    model = MicroEnterprise
    fields = ["code", "name", "me_type", "status", "department", "cost_center"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:micro_enterprise_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me_type"].queryset = MicroEnterpriseType.objects.filter(tenant=tenant)
            form.fields["status"].queryset = MicroEnterpriseStatus.objects.filter(tenant=tenant)
        return form


@method_decorator(login_required, name="dispatch")
class MicroEnterpriseDeleteView(TenantScopedMixin, DeleteView):
    model = MicroEnterprise
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:micro_enterprise_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


@method_decorator(login_required, name="dispatch")
class MicroEnterpriseDetailView(TenantScopedMixin, DetailView):
    model = MicroEnterprise
    context_object_name = "me"
    template_name = "platform_org/micro_enterprise_detail.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset().select_related("me_type", "status", "tenant"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get only top-level services for this ME (children will be rendered recursively)
        context["services"] = MEService.objects.filter(
            tenant=self.get_tenant(),
            provider_me=self.object,
            parent__isnull=True
        ).select_related("sla_template").prefetch_related("sub_services").order_by("name")
        return context


# -------------------------
# ME Service Catalog
# -------------------------
@method_decorator(login_required, name="dispatch")
class MEServiceListView(TenantScopedMixin, ListView):
    model = MEService
    context_object_name = "items"
    template_name = "platform_org/service_list.html"

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("provider_me", "sla_template", "parent"))
        q = self.request.GET.get("q")
        provider = self.request.GET.get("provider")
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if provider:
            qs = qs.filter(provider_me_id=provider)
        
        # If filtering by provider, we might want to show the tree for that provider
        # but the current logic only shows parents.
        if provider and not q:
            return qs.filter(parent__isnull=True).order_by("name")

        # Only show parent services in the main list
        return qs.filter(parent__isnull=True).order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        if tenant:
            context["mes"] = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
        return context


@method_decorator(login_required, name="dispatch")
class MEServiceCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = MEService
    fields = ["provider_me", "parent", "name", "description", "cost", "sla_template"]
    template_name = "platform_org/service_form.html"
    success_url = reverse_lazy("platform_org:service_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["provider_me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
            form.fields["parent"].queryset = MEService.objects.filter(tenant=tenant).order_by("name")
            from .core.models import SLATemplate
            form.fields["sla_template"].queryset = SLATemplate.objects.filter(tenant=tenant).order_by("name")
            
            # Pre-fill from GET parameters
            if self.request.method == "GET":
                parent_id = self.request.GET.get("parent")
                provider_me_id = self.request.GET.get("provider_me")
                if parent_id:
                    form.initial["parent"] = parent_id
                if provider_me_id:
                    form.initial["provider_me"] = provider_me_id
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        if tenant:
            from .core.models import SLATemplate
            context["sla_templates"] = SLATemplate.objects.filter(tenant=tenant).order_by("name")
        return context


@method_decorator(login_required, name="dispatch")
class MEServiceUpdateView(TenantScopedMixin, UpdateView):
    model = MEService
    fields = ["provider_me", "parent", "name", "description", "cost", "sla_template"]
    template_name = "platform_org/service_form.html"
    success_url = reverse_lazy("platform_org:service_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["provider_me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
            form.fields["parent"].queryset = MEService.objects.filter(tenant=tenant).exclude(id=self.object.id).order_by("name")
            from .core.models import SLATemplate
            form.fields["sla_template"].queryset = SLATemplate.objects.filter(tenant=tenant).order_by("name")
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        if tenant:
            from .core.models import SLATemplate
            context["sla_templates"] = SLATemplate.objects.filter(tenant=tenant).order_by("name")
        return context


@method_decorator(login_required, name="dispatch")
class MEServiceDeleteView(TenantScopedMixin, DeleteView):
    model = MEService
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:service_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


@method_decorator(login_required, name="dispatch")
class MEServiceDetailView(TenantScopedMixin, DetailView):
    model = MEService
    context_object_name = "s"
    template_name = "platform_org/service_detail.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset().select_related("provider_me", "sla_template", "parent"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.get_tenant()
        if tenant:
            from .core.models import SLATemplate
            context["sla_templates"] = SLATemplate.objects.filter(tenant=tenant).order_by("name")
        return context


@login_required
def service_sla_cost_manage(request, service_id):
    """Handle add/edit of ServiceSLACost"""
    from django.http import HttpResponse
    from .core.models import ServiceSLACost, SLATemplate
    
    tenant = request.tenant
    service = MEService.objects.filter(tenant=tenant, id=service_id).first()
    
    if not service:
        return HttpResponse(status=404)
    
    if request.method == "POST":
        sla_cost_id = request.POST.get("sla_cost_id")
        sla_template_id = request.POST.get("sla_template")
        cost = request.POST.get("cost")
        
        if sla_cost_id:
            # Edit existing
            sla_cost = ServiceSLACost.objects.filter(id=sla_cost_id, service=service).first()
            if sla_cost:
                sla_cost.cost = cost
                sla_cost.save()
        else:
            # Create new
            sla_template = SLATemplate.objects.filter(tenant=tenant, id=sla_template_id).first()
            if sla_template:
                ServiceSLACost.objects.update_or_create(
                    tenant=tenant,
                    service=service,
                    sla_template=sla_template,
                    defaults={"cost": cost}
                )
        
        return HttpResponse(status=200)
    
    return HttpResponse(status=405)


@login_required
def service_sla_cost_delete(request, service_id):
    """Handle delete of ServiceSLACost"""
    from django.http import HttpResponse, HttpResponseRedirect
    from django.urls import reverse
    from .core.models import ServiceSLACost
    
    tenant = request.tenant
    service = MEService.objects.filter(tenant=tenant, id=service_id).first()
    
    if not service:
        return HttpResponse(status=404)
    
    if request.method == "POST":
        sla_cost_id = request.POST.get("sla_cost_id")
        ServiceSLACost.objects.filter(id=sla_cost_id, service=service, tenant=tenant).delete()
        return HttpResponseRedirect(reverse("platform_org:service_detail", args=[service_id]))
    
    return HttpResponse(status=405)


# -------------------------
# Contracts
# -------------------------
@method_decorator(login_required, name="dispatch")
class ContractListView(TenantScopedMixin, ListView):
    model = MEContract
    context_object_name = "items"
    template_name = "platform_org/contract_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workflow_states"] = get_state_choices(self.get_tenant(), "CONTRACT") or [("DRAFT", "Draft"), ("ACTIVE", "Active"), ("SUSPENDED", "Suspended"), ("CLOSED", "Closed")]
        wf = get_active_workflow(self.get_tenant(), "CONTRACT")
        context["contract_workflow_name"] = wf.name if wf else "Default"
        return context

    def get_queryset(self):
        qs = self.scope_queryset(
            super()
            .get_queryset()
            .select_related("tenant", "provider_me", "consumer_me")
        )
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        provider = self.request.GET.get("provider")
        consumer = self.request.GET.get("consumer")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(provider_me__name__icontains=q) | Q(consumer_me__name__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if provider:
            qs = qs.filter(provider_me__id=provider)
        if consumer:
            qs = qs.filter(consumer_me__id=consumer)
        return qs.order_by("-start_date")


@method_decorator(login_required, name="dispatch")
class ContractCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = MEContract
    fields = ["code", "provider_me", "start_date", "end_date", "sla_template"]
    template_name = "platform_org/contract_form.html"
    success_url = reverse_lazy("platform_org:contract_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["provider_me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
            
            
            # sla_template is handled per-service in the contract_form.html table,
            # but we keep the field filtering if it exists in the form
            if "sla_template" in form.fields:
                try:
                    from .core.models import SLATemplate
                    form.fields["sla_template"].queryset = SLATemplate.objects.filter(tenant=tenant).order_by("name")
                except KeyError:
                    pass
            
            # Hide the old service field if it still exists in form
            if "service" in form.fields:
                del form.fields["service"]
        return form

    def post(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") == "XMLHttpRequest" and "provider_id" in request.POST:
            # Handle dynamic service loading
            provider_id = request.POST.get("provider_id")
            tenant = self.get_tenant()
            services = MEService.objects.filter(tenant=tenant, provider_me_id=provider_id).select_related("sla_template", "parent").prefetch_related("sla_costs")
            from .core.models import SLATemplate
            sla_templates = SLATemplate.objects.filter(tenant=tenant)
            
            data = {
                "services": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "parent_id": s.parent_id,
                        "cost": float(s.cost),
                        "sla_template_id": s.sla_template_id,
                        "sla_costs": {sc.sla_template_id: float(sc.cost) for sc in s.sla_costs.all()}
                    } for s in services
                ],
                "sla_templates": [
                    {"id": t.id, "name": t.name} for t in sla_templates
                ]
            }
            return JsonResponse(data)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        tenant = self.get_tenant()
        if tenant:
            form.instance.status = get_initial_state_code(tenant, "CONTRACT", "DRAFT")
            consumer_me = get_user_consumer_me(self.request.user, tenant)
            if consumer_me:
                form.instance.consumer_me = consumer_me
        # We need to call form_valid on CreateView which saves the object
        # But we also need to handle the case where it might fail or we need to add messages
        try:
            response = super().form_valid(form)
            # Handle the many-to-many services
            selected_services = self.request.POST.getlist("selected_services")
            tenant = self.get_tenant()
            
            # Recalculate contract value and save services
            total_value = 0
            selected_ids = [int(sid) for sid in selected_services]
            
            for svc_id in selected_services:
                service = MEService.objects.get(id=svc_id, tenant=tenant)
                sla_id = self.request.POST.get(f"sla_{svc_id}")
                billing_type = self.request.POST.get(f"billing_type_{svc_id}", "PERIOD")
                quantity = self.request.POST.get(f"quantity_{svc_id}")
                period_start = self.request.POST.get(f"period_start_{svc_id}")
                period_end = self.request.POST.get(f"period_end_{svc_id}")

                ContractService.objects.create(
                    tenant=tenant,
                    contract=self.object,
                    service=service,
                    sla_template_id=sla_id if sla_id else None,
                    billing_type=billing_type,
                    quantity=quantity if billing_type == "QUANTITY" and quantity else None,
                    period_start=period_start if billing_type == "PERIOD" and period_start else None,
                    period_end=period_end if billing_type == "PERIOD" and period_end else None,
                )
                
                # Logic for calculating contract value:
                # 1. If a service is a child AND its parent is also selected AND parent cost > 0, 
                #    skip this child's cost (double counting).
                # 2. Otherwise, add the service cost.
                
                # SLA-specific cost
                actual_cost = service.cost
                if sla_id:
                    from .core.models import ServiceSLACost
                    sla_cost_obj = ServiceSLACost.objects.filter(service=service, sla_template_id=sla_id).first()
                    if sla_cost_obj:
                        actual_cost = sla_cost_obj.cost

                should_add_cost = True
                if service.parent_id and service.parent_id in selected_ids:
                    parent_service = MEService.objects.get(id=service.parent_id, tenant=tenant)
                    # Check parent's actual cost with its selected SLA
                    parent_sla_id = self.request.POST.get(f"sla_{service.parent_id}")
                    parent_cost = parent_service.cost
                    if parent_sla_id:
                        from .core.models import ServiceSLACost
                        p_sla_cost_obj = ServiceSLACost.objects.filter(service=parent_service, sla_template_id=parent_sla_id).first()
                        if p_sla_cost_obj:
                            parent_cost = p_sla_cost_obj.cost
                    
                    if parent_cost > 0:
                        should_add_cost = False
                
                if should_add_cost:
                    if billing_type == "QUANTITY" and quantity:
                        total_value += actual_cost * float(quantity)
                    else:
                        total_value += actual_cost
            
            self.object.contract_value = total_value
            self.object.save()
            return response
        except Exception as e:
            from django.contrib import messages
            messages.error(self.request, f"Error saving contract: {e}")
            return self.form_invalid(form)

@method_decorator(login_required, name="dispatch")
class ContractUpdateView(TenantScopedMixin, UpdateView):
    model = MEContract
    fields = ["code", "provider_me", "start_date", "end_date", "sla_template"]
    template_name = "platform_org/contract_form.html"
    success_url = reverse_lazy("platform_org:contract_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["provider_me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
            

            # sla_template is handled per-service in the contract_form.html table,
            # but we keep the field filtering if it exists in the form
            if "sla_template" in form.fields:
                try:
                    from .core.models import SLATemplate
                    form.fields["sla_template"].queryset = SLATemplate.objects.filter(tenant=tenant).order_by("name")
                except KeyError:
                    pass

            if "service" in form.fields:
                del form.fields["service"]
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_services"] = self.object.contract_services.all()
        return ctx

    def form_valid(self, form):
        tenant = self.get_tenant()
        if tenant and not form.instance.status:
            form.instance.status = get_initial_state_code(tenant, "CONTRACT", "DRAFT")
        consumer_me = get_user_consumer_me(self.request.user, tenant)
        if consumer_me:
            form.instance.consumer_me = consumer_me
        try:
            response = super().form_valid(form)
            selected_services = self.request.POST.getlist("selected_services")
            tenant = self.get_tenant()
            
            # Clear existing and recreate
            self.object.contract_services.all().delete()
            
            total_value = 0
            selected_ids = [int(sid) for sid in selected_services]
            
            for svc_id in selected_services:
                service = MEService.objects.get(id=svc_id, tenant=tenant)
                sla_id = self.request.POST.get(f"sla_{svc_id}")
                billing_type = self.request.POST.get(f"billing_type_{svc_id}", "PERIOD")
                quantity = self.request.POST.get(f"quantity_{svc_id}")
                period_start = self.request.POST.get(f"period_start_{svc_id}")
                period_end = self.request.POST.get(f"period_end_{svc_id}")

                ContractService.objects.create(
                    tenant=tenant,
                    contract=self.object,
                    service=service,
                    sla_template_id=sla_id if sla_id else None,
                    billing_type=billing_type,
                    quantity=quantity if billing_type == "QUANTITY" and quantity else None,
                    period_start=period_start if billing_type == "PERIOD" and period_start else None,
                    period_end=period_end if billing_type == "PERIOD" and period_end else None,
                )
                
                # Logic for calculating contract value (mirroring frontend)
                # SLA-specific cost
                actual_cost = service.cost
                if sla_id:
                    from .core.models import ServiceSLACost
                    sla_cost_obj = ServiceSLACost.objects.filter(service=service, sla_template_id=sla_id).first()
                    if sla_cost_obj:
                        actual_cost = sla_cost_obj.cost

                should_add_cost = True
                if service.parent_id and service.parent_id in selected_ids:
                    # If the parent is selected and has a cost, we don't add the child's cost
                    parent_service = MEService.objects.get(id=service.parent_id, tenant=tenant)
                    
                    # Check parent's actual cost with its selected SLA
                    parent_sla_id = self.request.POST.get(f"sla_{service.parent_id}")
                    parent_cost = parent_service.cost
                    if parent_sla_id:
                        from .core.models import ServiceSLACost
                        p_sla_cost_obj = ServiceSLACost.objects.filter(service=parent_service, tenant=tenant, sla_template_id=parent_sla_id).first()
                        if p_sla_cost_obj:
                            parent_cost = p_sla_cost_obj.cost

                    if parent_cost > 0:
                        should_add_cost = False
                
                if should_add_cost:
                    if billing_type == "QUANTITY" and quantity:
                        total_value += actual_cost * float(quantity)
                    else:
                        total_value += actual_cost
            
            self.object.contract_value = total_value
            self.object.save()
            return response
        except Exception as e:
            from django.contrib import messages
            messages.error(self.request, f"Error updating contract: {e}")
            return self.form_invalid(form)


@method_decorator(login_required, name="dispatch")
class ContractDetailView(TenantScopedMixin, DetailView):
    model = MEContract
    context_object_name = "contract"
    template_name = "platform_org/contract_detail.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset().select_related("provider_me", "consumer_me"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workflow = get_active_workflow(self.get_tenant(), "CONTRACT")
        context["workflow"] = workflow
        return context


@method_decorator(login_required, name="dispatch")
class ContractDeleteView(TenantScopedMixin, DeleteView):
    model = MEContract
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:contract_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


# -------------------------
# VAM Agreements
# -------------------------
@method_decorator(login_required, name="dispatch")
class VAMAgreementListView(TenantScopedMixin, ListView):
    model = VAMAgreement
    context_object_name = "items"
    template_name = "platform_org/vam_list.html"

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("tenant", "me"))
        q = self.request.GET.get("q")
        me_id = self.request.GET.get("me")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(me__name__icontains=q) | Q(me__code__icontains=q))
        if me_id:
            qs = qs.filter(me__id=me_id)
        return qs.order_by("-created_at")


@method_decorator(login_required, name="dispatch")
class VAMAgreementCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = VAMAgreement
    fields = ["code", "me", "total_committed_amount"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:vam_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
        return form


@method_decorator(login_required, name="dispatch")
class VAMAgreementUpdateView(TenantScopedMixin, UpdateView):
    model = VAMAgreement
    fields = ["code", "me", "total_committed_amount"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:vam_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
        return form


@method_decorator(login_required, name="dispatch")
class VAMAgreementDeleteView(TenantScopedMixin, DeleteView):
    model = VAMAgreement
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:vam_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


# -------------------------
# KPIs
# -------------------------
@method_decorator(login_required, name="dispatch")
class KPIListView(TenantScopedMixin, ListView):
    model = MEKPI
    context_object_name = "items"
    template_name = "platform_org/kpi_list.html"

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("tenant", "me"))
        q = self.request.GET.get("q")
        me_id = self.request.GET.get("me")
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q) | Q(me__name__icontains=q))
        if me_id:
            qs = qs.filter(me__id=me_id)
        return qs.order_by("-created_at")


@method_decorator(login_required, name="dispatch")
class KPICreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = MEKPI
    fields = ["code", "me", "name", "target_value", "actual_value"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:kpi_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
        return form


@method_decorator(login_required, name="dispatch")
class KPIUpdateView(TenantScopedMixin, UpdateView):
    model = MEKPI
    fields = ["code", "me", "name", "target_value", "actual_value"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:kpi_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["me"].queryset = MicroEnterprise.objects.filter(tenant=tenant).order_by("name")
        return form


@method_decorator(login_required, name="dispatch")
class KPIDeleteView(TenantScopedMixin, DeleteView):
    model = MEKPI
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:kpi_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


# -------------------------
# Service Requests (SLA)
# -------------------------
@method_decorator(login_required, name="dispatch")
class ServiceRequestListView(TenantScopedMixin, ListView):
    model = ServiceRequest
    context_object_name = "items"
    template_name = "platform_org/service_request_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workflow_states"] = get_state_choices(self.get_tenant(), "REQUEST") or [("OPEN", "Open"), ("IN_PROGRESS", "In Progress"), ("RESOLVED", "Resolved"), ("CLOSED", "Closed")]
        wf = get_active_workflow(self.get_tenant(), "REQUEST")
        context["request_workflow_name"] = wf.name if wf else "Default"
        return context

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("tenant", "contract"))
        q = self.request.GET.get("q")
        status = self.request.GET.get("status")
        source = self.request.GET.get("source")
        contract = self.request.GET.get("contract")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(external_id__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if source:
            qs = qs.filter(source=source)
        if contract:
            qs = qs.filter(contract__id=contract)
        return qs.order_by("-opened_at")


@method_decorator(login_required, name="dispatch")
class ServiceRequestCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = ServiceRequest
    fields = [
        "external_id", "title", "source", "contract",
        "priority", "opened_at", "first_response_at", "resolved_at", "status",
    ]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:service_request_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["contract"].queryset = MEContract.objects.filter(tenant=tenant).order_by("-start_date")
            form.fields["status"].widget.choices = get_state_choices(tenant, "REQUEST") or [
                ("OPEN", "Open"),
                ("IN_PROGRESS", "In Progress"),
                ("RESOLVED", "Resolved"),
                ("CLOSED", "Closed"),
            ]
        return form


@method_decorator(login_required, name="dispatch")
class ServiceRequestUpdateView(TenantScopedMixin, UpdateView):
    model = ServiceRequest
    fields = [
        "external_id", "title", "source", "contract",
        "priority", "opened_at", "first_response_at", "resolved_at", "status",
    ]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:service_request_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["contract"].queryset = MEContract.objects.filter(tenant=tenant).order_by("-start_date")
            form.fields["status"].widget.choices = get_state_choices(tenant, "REQUEST") or [
                ("OPEN", "Open"),
                ("IN_PROGRESS", "In Progress"),
                ("RESOLVED", "Resolved"),
                ("CLOSED", "Closed"),
            ]
        return form


@method_decorator(login_required, name="dispatch")
class ServiceRequestDetailView(TenantScopedMixin, DetailView):
    model = ServiceRequest
    context_object_name = "request_item"
    template_name = "platform_org/service_request_detail.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset().select_related("contract"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workflow = get_active_workflow(self.get_tenant(), "REQUEST")
        context["workflow"] = workflow
        return context


@method_decorator(login_required, name="dispatch")
class ServiceRequestDeleteView(TenantScopedMixin, DeleteView):
    model = ServiceRequest
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:service_request_list")

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())


@method_decorator(login_required, name="dispatch")
class SLABreachesView(TenantScopedMixin, ListView):
    model = SLABreachEvent
    context_object_name = "items"
    template_name = "platform_org/sla_breaches.html"

    def get_queryset(self):
        qs = self.scope_queryset(super().get_queryset().select_related("request", "tenant", "request__contract"))
        breach_type = self.request.GET.get("breach_type")
        q = self.request.GET.get("q")
        if breach_type:
            qs = qs.filter(breach_type=breach_type)
        if q:
            qs = qs.filter(Q(request__title__icontains=q) | Q(request__external_id__icontains=q))
        return qs.order_by("-breach_at")


@method_decorator(login_required, name="dispatch")
class WorkflowDefinitionListView(TenantScopedMixin, ListView):
    model = WorkflowDefinition
    context_object_name = "items"
    template_name = "platform_org/workflow_definition_list.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset()).order_by("entity_type", "name")


@method_decorator(login_required, name="dispatch")
class WorkflowDefinitionCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = WorkflowDefinition
    fields = ["name", "entity_type", "is_active"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")


@method_decorator(login_required, name="dispatch")
class WorkflowDefinitionUpdateView(TenantScopedMixin, UpdateView):
    model = WorkflowDefinition
    fields = ["name", "entity_type", "is_active"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")


@method_decorator(login_required, name="dispatch")
class WorkflowDefinitionDeleteView(TenantScopedMixin, DeleteView):
    model = WorkflowDefinition
    template_name = "platform_org/confirm_delete.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")


@method_decorator(login_required, name="dispatch")
class WorkflowStateCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = WorkflowState
    fields = ["workflow", "code", "name", "order", "is_initial", "is_terminal"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["workflow"].queryset = WorkflowDefinition.objects.filter(tenant=tenant)
        return form


@method_decorator(login_required, name="dispatch")
class WorkflowTransitionCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = WorkflowTransition
    fields = ["workflow", "from_state", "to_state", "name"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            workflows = WorkflowDefinition.objects.filter(tenant=tenant)
            states = WorkflowState.objects.filter(tenant=tenant)
            form.fields["workflow"].queryset = workflows
            form.fields["from_state"].queryset = states
            form.fields["to_state"].queryset = states
        return form




@method_decorator(login_required, name="dispatch")
class WorkflowDefinitionDetailView(TenantScopedMixin, DetailView):
    model = WorkflowDefinition
    context_object_name = "workflow"
    template_name = "platform_org/workflow_definition_detail.html"

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        workflow = self.object
        context["states"] = workflow.states.all()
        context["transitions"] = workflow.transitions.select_related("from_state", "to_state")
        context["actions"] = workflow.actions.select_related("state")
        context["mermaid"] = build_mermaid(workflow)
        return context


@method_decorator(login_required, name="dispatch")
class WorkflowStateActionCreateView(TenantScopedMixin, TenantAssignMixin, CreateView):
    model = WorkflowStateAction
    fields = ["workflow", "state", "name", "action_type", "config", "is_active"]
    template_name = "platform_org/form.html"
    success_url = reverse_lazy("platform_org:workflow_definition_list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        tenant = self.get_tenant()
        if tenant:
            form.fields["workflow"].queryset = WorkflowDefinition.objects.filter(tenant=tenant)
            form.fields["state"].queryset = WorkflowState.objects.filter(tenant=tenant)
        return form

@login_required
def contract_transition(request, pk):
    if request.method != "POST":
        return redirect("platform_org:contract_list")
    tenant = request.tenant
    contract = MEContract.objects.filter(tenant=tenant, pk=pk).first()
    if not contract:
        return redirect("platform_org:contract_list")
    target_state = request.POST.get("target_state", "").strip()
    if target_state and can_transition(tenant, "CONTRACT", contract.status, target_state):
        contract.status = target_state
        contract.save(update_fields=["status", "updated_at"])
        execute_state_actions(contract, tenant, "CONTRACT", target_state)
    return redirect("platform_org:contract_list")


@login_required
def request_transition(request, pk):
    if request.method != "POST":
        return redirect("platform_org:service_request_list")
    tenant = request.tenant
    req = ServiceRequest.objects.filter(tenant=tenant, pk=pk).first()
    if not req:
        return redirect("platform_org:service_request_list")
    target_state = request.POST.get("target_state", "").strip()
    if target_state and can_transition(tenant, "REQUEST", req.status, target_state):
        req.status = target_state
        req.save(update_fields=["status"])
        execute_state_actions(req, tenant, "REQUEST", target_state)
    return redirect("platform_org:service_request_list")
