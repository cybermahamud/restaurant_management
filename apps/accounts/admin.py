# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Employee

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'get_location', 'is_active')
    list_filter = ('role', 'is_active',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 20
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Login Information', {
            'fields': ('username', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Role & Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Location Assignment', {
            'fields': ('restaurant', 'inventory'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined',),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'restaurant', 'inventory', 'password1', 'password2', 'is_active'),
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name() or '-'
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'first_name'
    
    def get_location(self, obj):
        if obj.restaurant:
            return format_html('<span style="color: #28a745;"><i class="fas fa-store"></i> {}</span>', obj.restaurant.name)
        elif obj.inventory:
            return format_html('<span style="color: #17a2b8;"><i class="fas fa-warehouse"></i> {}</span>', obj.inventory.name)
        return '-'
    get_location.short_description = 'Location'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New user
            obj.set_password(form.cleaned_data['password1'])
        super().save_model(request, obj, form, change)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'email', 'phone', 'position', 'department', 'get_assigned_location', 'is_active', )
    list_filter = ('department', 'employment_type', 'is_active',)
    search_fields = ('employee_id', 'name', 'email', 'phone', 'position')
    list_per_page = 20
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('employee_id', 'name', 'email', 'phone', 'address')
        }),
        ('Employment Details', {
            'fields': ('position', 'department', 'employment_type', 'salary', 'hire_date')
        }),
        ('Assignment', {
            'fields': ('restaurant', 'inventory'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def get_assigned_location(self, obj):
        if obj.restaurant:
            return format_html('<span style="color: #28a745;"><i class="fas fa-store"></i> {}</span>', obj.restaurant.name)
        elif obj.inventory:
            return format_html('<span style="color: #17a2b8;"><i class="fas fa-warehouse"></i> {}</span>', obj.inventory.name)
        return '-'
    get_assigned_location.short_description = 'Assigned Location'
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} employees activated.')
    make_active.short_description = 'Mark selected employees as active'
    
    def make_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} employees deactivated.')
    make_inactive.short_description = 'Mark selected employees as inactive'