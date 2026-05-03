# apps/orders/urls.py
from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('take-order/', views.take_order, name='take_order'),
    path('create-order/', views.create_order, name='create_order'),
    path('<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('<uuid:order_id>/edit/', views.edit_order, name='edit_order'),
    path('<uuid:order_id>/update/', views.update_order, name='update_order'),
    path('<uuid:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('<uuid:order_id>/add-item/', views.add_item_to_order, name='add_item_to_order'),
    path('<uuid:order_id>/kitchen-print/', views.kitchen_print, name='kitchen_print'),
    path('<uuid:order_id>/payment/', views.payment_page, name='payment_page'),
    path('<uuid:order_id>/process-payment/', views.process_payment, name='process_payment'),
    path('<uuid:order_id>/print-bill/', views.print_bill, name='print_bill'),  # Changed from 'bill' to 'print_bill'
    path('<uuid:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<uuid:order_id>/delete/', views.delete_order, name='delete_order'),
    path('<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # Waste Management
    path('waste/record/', views.record_waste, name='record_waste'),
    path('waste/list/', views.waste_list, name='waste_list'),

]