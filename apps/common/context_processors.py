# apps/common/context_processors.py
def user_roles(request):
    """Context processor to add role-based flags to all templates"""
    context = {
        'is_admin': False,
        'is_staff_role': False,
        'is_store_role': False,
        'has_full_access': False,
    }
    
    if request.user.is_authenticated:
        # Superuser has full access
        if request.user.is_superuser:
            context['is_admin'] = True
            context['is_staff_role'] = True
            context['is_store_role'] = True
            context['has_full_access'] = True
        else:
            role = request.user.role
            context['is_admin'] = (role == 'admin')
            context['is_staff_role'] = (role == 'staff')
            context['is_store_role'] = (role == 'store')
            context['has_full_access'] = (role == 'admin')
        
        context['user'] = request.user
    
    return context