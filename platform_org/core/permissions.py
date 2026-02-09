from rest_framework.permissions import BasePermission
from .models import MEOwner, MicroEnterprise, MEContract, VAMAgreement, MEKPI

def is_platform_admin(user) -> bool:
    return user and user.is_authenticated and (user.is_staff or user.groups.filter(name="Platform Admin").exists())

class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_platform_admin(request.user)

class RowLevelMEPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if is_platform_admin(request.user):
            return True
        if isinstance(obj, MicroEnterprise):
            return MEOwner.objects.filter(me=obj, user=request.user).exists()
        if isinstance(obj, MEContract):
            return (
                MEOwner.objects.filter(me=obj.provider_me, user=request.user).exists()
                or MEOwner.objects.filter(me=obj.consumer_me, user=request.user).exists()
            )
        if isinstance(obj, VAMAgreement):
            return MEOwner.objects.filter(me=obj.me, user=request.user).exists()
        if isinstance(obj, MEKPI):
            return MEOwner.objects.filter(me=obj.me, user=request.user).exists()
        return False
