from rest_framework.permissions import BasePermission, SAFE_METHODS
from accounts.models import User

class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool (request.user.is_authenticated and request.user.role == User.Role.FARMER)
    
class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and obj.farmer_id == request.user.id)