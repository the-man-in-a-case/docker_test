from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, "role", None) == "admin")

class IsTenant(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, "role", None) == "tenant")

class AdminOrTenantReadCreate(BasePermission):
    """
    - admin: 全部允许
    - tenant: 仅允许 SAFE_METHODS + POST(create 任务)；你可按业务精化
    """
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        role = getattr(u, "role", None)
        if role == "admin":
            return True
        if role == "tenant":
            if request.method in SAFE_METHODS:
                return True
            if request.method == "POST":
                return True
        return False
