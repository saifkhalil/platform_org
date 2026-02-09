from celery import shared_task
from django.utils import timezone
from .models import ServiceRequest, SLABreachEvent
from platform_org.core.notifications import send_teams_webhook

def _hours(opened_at, now):
    return (now - opened_at).total_seconds() / 3600.0

@shared_task
def check_sla_breaches():
    now = timezone.now()
    reqs = ServiceRequest.objects.select_related("contract", "tenant", "contract__sla_template").filter(
        status__in=["OPEN", "IN_PROGRESS"]
    )

    created = 0
    for r in reqs:
        template = r.contract.sla_template
        if not template:
            continue

        # Check Response Time
        if template.response_time_hours and r.first_response_at is None:
            if _hours(r.opened_at, now) > template.response_time_hours:
                _, created_flag = SLABreachEvent.objects.get_or_create(
                    tenant=r.tenant,
                    request=r,
                    breach_type="RESPONSE",
                    defaults={"details": {"target_hours": template.response_time_hours}}
                )
                if created_flag:
                    send_teams_webhook(f"SLA BREACH (RESPONSE): {r.title} | Contract {r.contract.code}")
                    created += 1

        # Check Resolution Time
        if template.resolution_time_hours and r.resolved_at is None:
            if _hours(r.opened_at, now) > template.resolution_time_hours:
                _, created_flag = SLABreachEvent.objects.get_or_create(
                    tenant=r.tenant,
                    request=r,
                    breach_type="RESOLUTION",
                    defaults={"details": {"target_hours": template.resolution_time_hours}}
                )
                if created_flag:
                    send_teams_webhook(f"SLA BREACH (RESOLUTION): {r.title} | Contract {r.contract.code}")
                    created += 1
    return {"created": created}
