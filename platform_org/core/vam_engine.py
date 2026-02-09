from celery import shared_task
from django.utils import timezone
from platform_org.core.models import MicroEnterprise, MEKPI, VAMAgreement, VAMTranche
from platform_org.sla.models import SLABreachEvent

@shared_task
def compute_autonomy_scores():
    now = timezone.now()
    month_key = now.strftime("%Y-%m")
    updated = 0

    for me in MicroEnterprise.objects.all():
        breaches = SLABreachEvent.objects.filter(tenant=me.tenant, request__contract__provider_me=me).count()
        kpis = MEKPI.objects.filter(tenant=me.tenant, me=me)
        kpi_hit = 0
        for k in kpis:
            if k.target_value is not None and k.actual_value is not None and k.actual_value >= k.target_value:
                kpi_hit += 1

        score = max(0, min(100, 100 - breaches * 10 + kpi_hit * 5))

        if score >= 80:
            me.autonomy_level = "HIGH"
        elif score >= 50:
            me.autonomy_level = "STANDARD"
        else:
            me.autonomy_level = "RESTRICTED"
        me.save(update_fields=["autonomy_level","updated_at"])
        updated += 1

        # Tranche auto release policy: if score>=70 => release pending
        for ag in VAMAgreement.objects.filter(tenant=me.tenant, me=me, status="ACTIVE"):
            for tr in VAMTranche.objects.filter(tenant=me.tenant, agreement=ag, status="PENDING"):
                if score >= 70:
                    tr.status = "RELEASED"
                    tr.released_on = now.date()
                    tr.save(update_fields=["status","released_on","updated_at"])

    return {"month": month_key, "updated": updated}
