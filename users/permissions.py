from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
    	if request.method in permissions.SAFE_METHODS:
    		return True
    	else:
    		return obj.id == request.user.id

class IsSenderOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow sender of a service to edit it.
    """
    def has_object_permission(self, request, view, obj):
    	if request.method in permissions.SAFE_METHODS:
    		return True
    	else:
    		return obj.sender == request.user.id


class IsAuthenticatedOrCreate(permissions.BasePermission):
    """
    Allows access only to authenticated users for other operations than creating a user.
    """

    def has_permission(self, request, view):
    	if request.method == 'POST':
    		return True
    	else:
        	return request.user and request.user.is_authenticated