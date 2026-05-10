# apps/inventory/urls.py
from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    
    # Inventory Management
    path('inventories/', views.inventory_list, name='inventory_list'),
    path('inventories/create/', views.create_inventory, name='create_inventory'),
    path('inventories/<uuid:pk>/edit/', views.edit_inventory, name='edit_inventory'),
    path('inventories/<uuid:pk>/delete/', views.delete_inventory, name='delete_inventory'),
    
    # Categories
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<uuid:pk>/edit/', views.edit_category, name='edit_category'),
    path('categories/<uuid:pk>/delete/', views.delete_category, name='delete_category'),
    path('categories/create-ajax/', views.create_category_ajax, name='create_category_ajax'),
    
    # Raw Materials
    path('raw-materials/', views.raw_material_list, name='raw_material_list'),
    path('raw-materials/create/', views.create_raw_material, name='create_raw_material'),
    path('raw-materials/<uuid:pk>/edit/', views.edit_raw_material, name='edit_raw_material'),
    path('raw-materials/<uuid:pk>/delete/', views.delete_raw_material, name='delete_raw_material'),
    
    # Stock Management
    path('current-stock/', views.current_stock, name='current_stock'),
    path('stock/<uuid:pk>/', views.stock_detail, name='stock_detail'),
    path('raw-materials/<uuid:pk>/add-stock/', views.add_stock, name='add_stock'),
    path('raw-materials/<uuid:pk>/update-stock/', views.update_stock, name='update_stock'),
    path('transactions/<uuid:pk>/edit/', views.edit_transaction, name='edit_transaction'), 
    path('transactions/<uuid:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    
    # Stock Requests
    path('stock-requests/', views.stock_requests_list, name='stock_requests_list'),
    path('stock-requests/create-ajax/', views.create_stock_request_ajax, name='create_stock_request_ajax'),
    path('stock-requests/<uuid:pk>/process/', views.process_stock_request, name='process_stock_request'),
    path('stock-requests/<uuid:pk>/fulfill/', views.fulfill_stock_request, name='fulfill_stock_request'),
    
    # Daily Stock Request (Staff)
    path('daily-request/create/', views.daily_request_create, name='daily_request_create'),
    path('daily-request/list/', views.daily_request_list, name='daily_request_list'),
    path('daily-request/<uuid:pk>/', views.daily_request_detail, name='daily_request_detail'),
    
    # Admin/Store URLs
    path('all-requests/', views.all_requests_list, name='all_requests_list'),
    path('consolidated-summary/', views.consolidated_summary, name='consolidated_summary'),
    path('production-batch/add/', views.add_production_batch, name='add_production_batch'),
    path('production-batches/', views.production_batches, name='production_batches'),
    path('dispatch/<uuid:request_id>/', views.dispatch_to_restaurant, name='dispatch_to_restaurant'),
    path('production-batch/generate/', views.generate_production_batch, name='generate_production_batch'),

    path('purchase-summary/', views.purchase_summary, name='purchase_summary'),
    path('item-transactions/<uuid:item_id>/', views.item_transactions, name='item_transactions'),
    path('production-dispatch-report/', views.production_dispatch_report, name='production_dispatch_report'),
    path('dispatch-details/<uuid:product_id>/<uuid:restaurant_id>/', views.dispatch_details, name='dispatch_details'),
    path('product-dispatch-details/<uuid:product_id>/', views.product_dispatch_details, name='product_dispatch_details'),
]