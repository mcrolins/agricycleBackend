from rest_framework.permissions import BasePermission

from accounts.models import User

class IsProcessor(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.PROCESSOR)

class IsFarmer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.FARMER)

class IsRequestParticipant(BasePermission):
    """
    Only the farmer who owns the listing OR the processor who created the request.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return obj.processor_id == user.id or obj.listing.farmer_id == user.id
