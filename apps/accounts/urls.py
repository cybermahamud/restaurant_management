# apps/accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User Profile
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    # User Management
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<uuid:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<uuid:user_id>/reset-password/', views.reset_user_password, name='reset_user_password'),
    path('users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<uuid:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Employee Management
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.create_employee, name='create_employee'),
    path('employees/<uuid:pk>/edit/', views.edit_employee, name='edit_employee'),
    path('employees/<uuid:pk>/delete/', views.delete_employee, name='delete_employee'),
    path('employees/<uuid:pk>/activate/', views.activate_employee, name='activate_employee'),
]