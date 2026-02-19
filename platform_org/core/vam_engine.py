from celery import shared_task

from platform_org.core.models import MEKPI, MicroEnterprise
from platform_org.sla.models import SLABreachEvent


@shared_task
def compute_autonomy_scores():
    updated = 0
    for me in MicroEnterprise.objects.select_related("tenant").all():
        breaches = SLABreachEvent.objects.filter(tenant=me.tenant, request__contract__provider_me=me).count()
        kpis = MEKPI.objects.filter(tenant=me.tenant, me=me)
        kpi_hit = sum(
            1
            for k in kpis
            if k.target_value is not None and k.actual_value is not None and k.actual_value >= k.target_value
        )

        score = max(0, min(100, 100 - breaches * 10 + kpi_hit * 5))
        if score >= 80:
            me.autonomy_level = "HIGH"
        elif score >= 50:
            me.autonomy_level = "STANDARD"
        else:
            me.autonomy_level = "RESTRICTED"

        me.save(update_fields=["autonomy_level", "updated_at"])
        updated += 1

    return {"updated": updated}
