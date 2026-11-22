from rest_framework.permissions import BasePermission

ROLE_PERMS={
    'super_admin':{'*'},
    'store_admin':{'products','orders','customers','marketing','settings','reports','content'},
    'product_manager':{'products'},
    'order_manager':{'orders'},
    'content_manager':{'content','marketing'},
    'customer':set(),
}
def user_has_perm(user, perm):
    return bool(user and user.is_authenticated and user.is_active and (
        user.is_superuser or '*' in ROLE_PERMS.get(user.role,set()) or perm in ROLE_PERMS.get(user.role,set())))
def role_perm(perm):
    class RolePermission(BasePermission):
        message='You do not have permission to perform this action.'
        def has_permission(self, request, view): return user_has_perm(request.user,perm)
    return RolePermission
