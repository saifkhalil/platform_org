from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from django.utils import timezone
from platform_org.core.models import (
    MicroEnterprise, MEOwner, MEContract, VAMAgreement, SLATemplate, MEKPI,
    MicroEnterpriseType, MicroEnterpriseStatus, ContractStatus
)
from platform_org.tenancy.models import Tenant

class Command(BaseCommand):
    help = "Seed Platform Org with groups and demo data"
    def handle(self, *args, **options):
        # Ensure default tenant exists
        tenant, _ = Tenant.objects.get_or_create(code="default", defaults={"name": "Default Tenant"})

        g_admin, _ = Group.objects.get_or_create(name="Platform Admin")
        Group.objects.get_or_create(name="ME Owner")
        Group.objects.get_or_create(name="ME Member")

        admin, created = User.objects.get_or_create(username="admin")
        if created:
            admin.set_password("admin")
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        admin.groups.add(g_admin)

        # Seed Types and Statuses
        t_node, _ = MicroEnterpriseType.objects.get_or_create(tenant=tenant, code="NODE_ME", defaults={"name": "Node ME"})
        t_ssp, _ = MicroEnterpriseType.objects.get_or_create(tenant=tenant, code="SSP", defaults={"name": "Shared Service Platform"})
        
        s_active, _ = MicroEnterpriseStatus.objects.get_or_create(tenant=tenant, code="ACTIVE", defaults={"name": "Active"})
        s_inc, _ = MicroEnterpriseStatus.objects.get_or_create(tenant=tenant, code="INCUBATION", defaults={"name": "Incubation"})

        cs_draft, _ = ContractStatus.objects.get_or_create(tenant=tenant, code="DRAFT", defaults={"name": "Draft"})
        cs_active, _ = ContractStatus.objects.get_or_create(tenant=tenant, code="ACTIVE", defaults={"name": "Active"})
        cs_expired, _ = ContractStatus.objects.get_or_create(tenant=tenant, code="EXPIRED", defaults={"name": "Expired"})

        me1, _ = MicroEnterprise.objects.get_or_create(
            code="ME-OPS", 
            defaults={"tenant": tenant, "name": "Operations ME", "me_type": t_node, "status": s_active}
        )
        me2, _ = MicroEnterprise.objects.get_or_create(
            code="ME-IT", 
            defaults={"tenant": tenant, "name": "IT Services ME", "me_type": t_ssp, "status": s_active}
        )
        MEOwner.objects.get_or_create(me=me1, user=admin, defaults={"role_in_me":"Owner","is_primary":True})
        MEOwner.objects.get_or_create(me=me2, user=admin, defaults={"role_in_me":"Owner","is_primary":True})

        SLATemplate.objects.get_or_create(name="Standard SLA", defaults={"response_time_hours":4,"resolution_time_hours":24,"availability_percent":99.5})
        MEContract.objects.get_or_create(code="C-0001", defaults={"provider_me":me2,"consumer_me":me1,"start_date":timezone.now().date(),"contract_value":100000,"status":cs_draft})
        VAMAgreement.objects.get_or_create(code="VAM-0001", defaults={"me":me2,"total_committed_amount":500000})
        MEKPI.objects.get_or_create(code="KPI-DEL-01", defaults={"me":me2,"name":"Delivery On-Time %","target_value":95})
        self.stdout.write(self.style.SUCCESS("Seed completed."))
