# apps/common/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def role_required(allowed_roles=[]):
    """Role-based access decorator with superadmin bypass"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            # Superadmin or superuser can access everything
            if request.user.is_superuser or request.user.role == 'superadmin':
                return view_func(request, *args, **kwargs)
            
            # Check if user's role is allowed
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied
        return wrapper
    return decorator

def permission_required(permission):
    """Permission-based access decorator with superadmin bypass"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            # Superadmin or superuser can access everything
            if request.user.is_superuser or request.user.role == 'superadmin':
                return view_func(request, *args, **kwargs)
            
            if request.user.has_perm(permission):
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'You do not have the required permission.')
            raise PermissionDenied
        return wrapper
    return decorator