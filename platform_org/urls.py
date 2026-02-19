from django.urls import path

from .views import (
    DashboardView,

    MicroEnterpriseListView, MicroEnterpriseCreateView, MicroEnterpriseUpdateView, MicroEnterpriseDeleteView, MicroEnterpriseDetailView,
    MEServiceListView, MEServiceCreateView, MEServiceUpdateView, MEServiceDeleteView, MEServiceDetailView,
    service_sla_cost_manage, service_sla_cost_delete,
    ContractListView, ContractCreateView, ContractUpdateView, ContractDeleteView,
    VAMAgreementListView, VAMAgreementCreateView, VAMAgreementUpdateView, VAMAgreementDeleteView,
    KPIListView, KPICreateView, KPIUpdateView, KPIDeleteView,
    ServiceRequestListView, ServiceRequestCreateView, ServiceRequestUpdateView, ServiceRequestDeleteView,
    SLABreachesView,
    WorkflowDefinitionListView, WorkflowDefinitionCreateView, WorkflowDefinitionUpdateView, WorkflowDefinitionDeleteView, WorkflowDefinitionDetailView,
    WorkflowStateCreateView, WorkflowTransitionCreateView, WorkflowStateActionCreateView,
    contract_transition, request_transition,
)

app_name = "platform_org"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),

    path("micro-enterprises/", MicroEnterpriseListView.as_view(), name="micro_enterprise_list"),
    path("micro-enterprises/new/", MicroEnterpriseCreateView.as_view(), name="micro_enterprise_create"),
    path("micro-enterprises/<int:pk>/", MicroEnterpriseDetailView.as_view(), name="micro_enterprise_detail"),
    path("micro-enterprises/<int:pk>/edit/", MicroEnterpriseUpdateView.as_view(), name="micro_enterprise_edit"),
    path("micro-enterprises/<int:pk>/delete/", MicroEnterpriseDeleteView.as_view(), name="micro_enterprise_delete"),

    path("services/", MEServiceListView.as_view(), name="service_list"),
    path("services/new/", MEServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/", MEServiceDetailView.as_view(), name="service_detail"),
    path("services/<int:pk>/edit/", MEServiceUpdateView.as_view(), name="service_edit"),
    path("services/<int:pk>/delete/", MEServiceDeleteView.as_view(), name="service_delete"),
    path("services/<int:service_id>/sla-cost/manage/", service_sla_cost_manage, name="service_sla_cost_manage"),
    path("services/<int:service_id>/sla-cost/delete/", service_sla_cost_delete, name="service_sla_cost_delete"),

    path("contracts/", ContractListView.as_view(), name="contract_list"),
    path("contracts/new/", ContractCreateView.as_view(), name="contract_create"),
    path("contracts/<int:pk>/edit/", ContractUpdateView.as_view(), name="contract_edit"),
    path("contracts/<int:pk>/delete/", ContractDeleteView.as_view(), name="contract_delete"),

    path("vam/", VAMAgreementListView.as_view(), name="vam_list"),
    path("vam/new/", VAMAgreementCreateView.as_view(), name="vam_create"),
    path("vam/<int:pk>/edit/", VAMAgreementUpdateView.as_view(), name="vam_edit"),
    path("vam/<int:pk>/delete/", VAMAgreementDeleteView.as_view(), name="vam_delete"),

    path("kpis/", KPIListView.as_view(), name="kpi_list"),
    path("kpis/new/", KPICreateView.as_view(), name="kpi_create"),
    path("kpis/<int:pk>/edit/", KPIUpdateView.as_view(), name="kpi_edit"),
    path("kpis/<int:pk>/delete/", KPIDeleteView.as_view(), name="kpi_delete"),

    path("requests/", ServiceRequestListView.as_view(), name="service_request_list"),
    path("requests/new/", ServiceRequestCreateView.as_view(), name="service_request_create"),
    path("requests/<int:pk>/edit/", ServiceRequestUpdateView.as_view(), name="service_request_edit"),
    path("requests/<int:pk>/delete/", ServiceRequestDeleteView.as_view(), name="service_request_delete"),

    path("sla/breaches/", SLABreachesView.as_view(), name="sla_breaches"),

    path("workflow/", WorkflowDefinitionListView.as_view(), name="workflow_definition_list"),
    path("workflow/new/", WorkflowDefinitionCreateView.as_view(), name="workflow_definition_create"),
    path("workflow/<int:pk>/", WorkflowDefinitionDetailView.as_view(), name="workflow_definition_detail"),
    path("workflow/<int:pk>/edit/", WorkflowDefinitionUpdateView.as_view(), name="workflow_definition_edit"),
    path("workflow/<int:pk>/delete/", WorkflowDefinitionDeleteView.as_view(), name="workflow_definition_delete"),
    path("workflow/states/new/", WorkflowStateCreateView.as_view(), name="workflow_state_create"),
    path("workflow/transitions/new/", WorkflowTransitionCreateView.as_view(), name="workflow_transition_create"),
    path("workflow/actions/new/", WorkflowStateActionCreateView.as_view(), name="workflow_action_create"),

    path("contracts/<int:pk>/transition/", contract_transition, name="contract_transition"),
    path("requests/<int:pk>/transition/", request_transition, name="request_transition"),
]
