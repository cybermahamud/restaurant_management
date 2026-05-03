# apps/reports/urls.py
from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Main Dashboard
    path('', views.reports_dashboard, name='reports_dashboard'),
    
    # Sales Reports
    path('sales/', views.sales_report, name='sales_report'),
    path('sales/daily/', views.daily_sales_report, name='daily_sales_report'),
    path('sales/monthly/', views.monthly_sales_report, name='monthly_sales_report'),
    
    # Financial Reports
    path('profit/', views.profit_report, name='profit_report'),
    path('profit/loss/', views.profit_loss_report, name='profit_loss_report'),
    
    # Wastage Reports
    path('wastage/', views.wastage_report, name='wastage_report'),
    path('wastage/daily/', views.daily_wastage_report, name='daily_wastage_report'),
    
    # Inventory Reports
    path('inventory/', views.inventory_report, name='inventory_report'),
    path('inventory/stock-value/', views.stock_value_report, name='stock_value_report'),
    
    # Business Reports (Admin only)
    path('business-summary/', views.business_summary, name='business_summary'),
    path('advanced/', views.advanced_report, name='advanced_report'),
    
    # Export
    path('export/<str:report_type>/', views.export_report, name='export_report'),
]