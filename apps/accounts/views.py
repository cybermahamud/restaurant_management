# apps/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import JsonResponse
from .models import User, Employee
from .forms import (UserLoginForm, UserCreateForm, UserEditForm, EmployeeForm, 
                    ChangePasswordForm, ResetPasswordForm)

# ==================== Authentication ====================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user and user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                return redirect('common:dashboard')
            else:
                messages.error(request, 'Invalid username or password or account is disabled')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out')
    return redirect('accounts:login')


# ==================== User Management ====================

@login_required
def user_list(request):
    """List all users - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    users = User.objects.all().order_by('-date_joined')
    
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def create_user(request):
    """Create new user - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.username}" created successfully')
            return redirect('accounts:user_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreateForm()
    
    return render(request, 'accounts/user_form.html', {
        'form': form, 
        'title': 'Create User'  # Make sure title is 'Create User'
    })


@login_required
def edit_user(request, user_id):
    """Edit user - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.username}" updated successfully')
            return redirect('accounts:user_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Edit User', 'user': user})


@login_required
def reset_user_password(request, user_id):
    """Reset user password - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Password reset for "{user.username}" successfully')
            return redirect('accounts:user_list')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ResetPasswordForm()
    
    return render(request, 'accounts/reset_password.html', {'form': form, 'user': user})


@login_required
def toggle_user_status(request, user_id):
    """Activate/deactivate user - admin only"""
    if not request.user.is_admin_user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    return JsonResponse({'success': True, 'message': f'User {status}'})


@login_required
def delete_user(request, user_id):
    """Delete user - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('accounts:user_list')
    
    user = get_object_or_404(User, id=user_id)
    
    if user == request.user:
        messages.error(request, 'You cannot delete your own account')
        return redirect('accounts:user_list')
    
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted successfully')
    return redirect('accounts:user_list')


# ==================== Profile & Password ====================

@login_required
def profile_view(request):
    """View and edit user profile"""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'Profile updated successfully')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/profile.html', {'user': request.user})


@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        user = request.user
        
        if not user.check_password(form.data.get('old_password')):
            messages.error(request, 'Current password is incorrect')
        elif form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password changed successfully')
            return redirect('accounts:profile')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = ChangePasswordForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


# ==================== Employee Management ====================

@login_required
def employee_list(request):
    """List all employees - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    employees = Employee.objects.all().order_by('-is_active', 'name')
    
    # Get filter parameters
    search_query = request.GET.get('search', '')
    department = request.GET.get('department', '')
    status = request.GET.get('status', '')
    
    # Apply filters
    if search_query:
        employees = employees.filter(
            Q(employee_id__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if department:
        employees = employees.filter(department=department)
    
    if status == 'active':
        employees = employees.filter(is_active=True)
    elif status == 'inactive':
        employees = employees.filter(is_active=False)
    
    # Statistics
    total_employees = Employee.objects.count()
    active_count = Employee.objects.filter(is_active=True).count()
    total_salary = Employee.objects.aggregate(total=Sum('salary'))['total'] or 0
    
    # Pagination
    paginator = Paginator(employees, 20)
    page = request.GET.get('page')
    employees = paginator.get_page(page)
    
    context = {
        'employees': employees,
        'total_employees': total_employees,
        'active_count': active_count,
        'inactive_count': total_employees - active_count,
        'total_salary': total_salary,
        'search_query': search_query,
        'department': department,
        'status': status,
    }
    return render(request, 'accounts/employee_list.html', context)


@login_required
def create_employee(request):
    """Create new employee - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'Employee "{employee.name}" created successfully')
            return redirect('accounts:employee_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = EmployeeForm()
    
    return render(request, 'accounts/employee_form.html', {'form': form, 'title': 'Create Employee'})


@login_required
def edit_employee(request, pk):
    """Edit employee - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    employee = get_object_or_404(Employee, id=pk)
    
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f'Employee updated successfully')
            return redirect('accounts:employee_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = EmployeeForm(instance=employee)
    
    return render(request, 'accounts/employee_form.html', {'form': form, 'title': 'Edit Employee', 'employee': employee})


@login_required
def delete_employee(request, pk):
    """Delete employee - admin only"""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    employee = get_object_or_404(Employee, id=pk)
    employee.delete()
    messages.success(request, 'Employee deleted successfully')
    return redirect('accounts:employee_list')


@login_required
def activate_employee(request, pk):
    """Activate employee - admin only"""
    if not request.user.is_admin_user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    employee = get_object_or_404(Employee, id=pk)
    employee.is_active = True
    employee.save()
    
    return JsonResponse({'success': True, 'message': 'Employee activated'})
