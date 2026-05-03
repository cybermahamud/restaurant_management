# apps/restaurant/urls.py
from django.urls import path
from . import views

app_name = 'restaurant'

urlpatterns = [
    # Restaurant Management
    path('', views.restaurant_list, name='list'),
    path('create/', views.create_restaurant, name='create'),
    path('<uuid:pk>/edit/', views.edit_restaurant, name='edit'),
    path('<uuid:pk>/delete/', views.delete_restaurant, name='delete'),
    
    # Table Management
    path('<uuid:restaurant_id>/tables/', views.manage_tables, name='manage_tables'),
    path('tables/<uuid:pk>/delete/', views.delete_table, name='delete_table'),
    path('tables/<uuid:table_id>/update-status/', views.update_table_status, name='update_table_status'),
    path('tables/<uuid:table_id>/update/', views.update_table, name='update_table'),
    
    # Menu Management
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/create/', views.create_menu_item, name='create_menu_item'),
    path('menu/<uuid:pk>/edit/', views.edit_menu_item, name='edit_menu_item'),
    path('menu/<uuid:pk>/delete/', views.delete_menu_item, name='delete_menu_item'),
    
    # Recipe Management
    path('menu/<uuid:menu_item_id>/recipes/', views.manage_recipes, name='manage_recipes'),
    path('recipes/<uuid:pk>/delete/', views.delete_recipe, name='delete_recipe'),
    
    # Set Menu Management
    path('set-menus/', views.set_menu_list, name='set_menu_list'),
    path('set-menus/create/', views.create_set_menu, name='create_set_menu'),
    path('set-menus/<uuid:pk>/edit/', views.edit_set_menu, name='edit_set_menu'),
    path('set-menus/<uuid:pk>/delete/', views.delete_set_menu, name='delete_set_menu'),
    
    # Stock Status
    path('stock-status/', views.stock_status, name='stock_status'),
    # path('add-stock-direct/', views.add_stock_direct, name='add_stock_direct'),
    

    # Category Management
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<uuid:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/<uuid:pk>/delete/', views.delete_category, name='delete_category'),
]