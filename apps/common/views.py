# apps/common/views.py - Complete fixed version
import json
from multiprocessing import context

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from apps.orders.models import Order, OrderItem, WasteRecord
from apps.restaurant.models import Restaurant, MenuItem
from apps.inventory.models import Inventory, RawMaterial, StockRequest, StockTransaction
from apps.accounts.models import User, Employee

@login_required
def dashboard(request):
    """Main dashboard view based on user role"""
    user = request.user
    
    # Check for superadmin or superuser first
    if user.is_superuser or user.role == 'superadmin':
        return admin_dashboard(request)
    elif user.role == 'admin':
        return admin_dashboard(request)
    elif user.role == 'staff':
        return staff_dashboard(request)
    elif user.role == 'store':
        return store_dashboard(request)
    else:
        # Default fallback
        return render(request, 'common/dashboard.html')
    

def staff_dashboard(request):
    """Staff dashboard for restaurant employees"""
    # Check if staff user has a restaurant assigned
    if not request.user.restaurant:
        context = {
            'no_restaurant': True,
            'message': 'No restaurant assigned to your account. Please contact administrator.'
        }
        return render(request, 'common/staff_dashboard.html', context)
    
    restaurant = request.user.restaurant
    today = timezone.now().date()
    
    # Get all occupied tables with their active orders
    occupied_tables = restaurant.tables.filter(status='occupied')
    
    # Get the active order for each occupied table
    occupied_tables_with_orders = []
    for table in occupied_tables:
        # Find the active order for this table (pending, confirmed, preparing)
        active_order = Order.objects.filter(
            restaurant=restaurant,
            table=table,
            status__in=['pending', 'confirmed', 'preparing']
        ).first()
        
        if active_order:
            occupied_tables_with_orders.append({
                'table': table,
                'order': active_order
            })
    
    # Calculate total income (from completed and paid orders)
    total_income = Order.objects.filter(
        restaurant=restaurant,
        status='completed',
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Count completed orders
    completed_orders_count = Order.objects.filter(
        restaurant=restaurant,
        status='completed'
    ).count()
    
    # Available tables count
    available_tables = restaurant.tables.filter(status='available').count()
    
    # Active orders count
    active_orders = Order.objects.filter(
        restaurant=restaurant,
        status__in=['pending', 'confirmed', 'preparing']
    ).count()
    
    # Low stock items
    from django.db.models import F
    low_stock_items = RawMaterial.objects.filter(
        current_stock__lte=F('minimum_stock')
    )[:10]
    
    context = {
        'restaurant': restaurant,
        'occupied_tables_with_orders': occupied_tables_with_orders,
        'total_income': total_income,
        'completed_orders_count': completed_orders_count,
        'available_tables': available_tables,
        'active_orders': active_orders,
        'low_stock_items': low_stock_items,
    }
    
    return render(request, 'common/staff_dashboard.html', context)


def store_dashboard(request):
    """Store/Inventory manager dashboard"""
    # Check if store user has an inventory assigned
    if not request.user.inventory:
        context = {
            'no_inventory': True,
            'message': 'No inventory assigned to your account. Please contact administrator.'
        }
        return render(request, 'common/store_dashboard.html', context)
    
    inventory = request.user.inventory
    
    # Stock metrics
    total_products = RawMaterial.objects.filter(inventory=inventory).count()
    low_stock_items = RawMaterial.objects.filter(
        inventory=inventory,
        current_stock__lte=F('minimum_stock')
    )
    low_stock_count = low_stock_items.count()
    
    # Stock value
    total_value = 0
    for item in RawMaterial.objects.filter(inventory=inventory):
        total_value += item.current_stock * item.unit_cost
    
    # Pending requests
    pending_requests = StockRequest.objects.filter(
        inventory=inventory,
        status='pending'
    ).count()
    
    context = {
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items[:10],
        'total_value': total_value,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'common/store_dashboard.html', context)

def manager_dashboard(request):
    """Restaurant manager dashboard"""
    if not request.user.restaurant:
        messages.error(request, 'No restaurant assigned')
        return redirect('common:dashboard')
    
    restaurant = request.user.restaurant
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # Sales metrics
    today_sales = Order.objects.filter(
        restaurant=restaurant,
        created_at__date=today,
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    month_sales = Order.objects.filter(
        restaurant=restaurant,
        created_at__date__gte=start_of_month,
        payment_status='paid'
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    total_orders = Order.objects.filter(restaurant=restaurant).count()
    avg_order_value = month_sales / Order.objects.filter(
        restaurant=restaurant,
        created_at__date__gte=start_of_month
    ).count() if total_orders > 0 else 0
    
    context = {
        'restaurant': restaurant,
        'today_sales': today_sales,
        'month_sales': month_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
    }
    
    return render(request, 'common/manager_dashboard.html', context)

from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        order = get_object_or_404(Order, id=order_id)
        
        # Check permission - staff can only update orders in their restaurant
        if request.user.role == 'staff' and order.restaurant != request.user.restaurant:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Update status
        order.status = new_status
        
        # If order is completed, update payment status if not already paid
        if new_status == 'completed' and order.payment_status == 'pending':
            order.payment_status = 'paid'
        
        order.save()
        
        return JsonResponse({'success': True, 'message': f'Order status updated to {new_status}'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    


# apps/common/views.py - Complete admin_dashboard function

@login_required
def admin_dashboard(request):
    """Admin dashboard with comprehensive summaries and filters"""
    
    # Get filter parameters
    restaurant_id = request.GET.get('restaurant')
    inventory_id = request.GET.get('inventory')
    date_range = request.GET.get('date_range', 'today')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    view_type = request.GET.get('view', 'restaurant')
    
    # Set date range
    today = timezone.now().date()
    
    # Initialize dates
    start_date = today
    end_date = today
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_range = 'custom'
        except (ValueError, TypeError):
            start_date = today
            end_date = today
            date_range = 'today'
    elif date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(days=1)
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_range == 'last_month':
        first_day_of_month = today.replace(day=1)
        last_day_of_prev_month = first_day_of_month - timedelta(days=1)
        start_date = last_day_of_prev_month.replace(day=1)
        end_date = last_day_of_prev_month
    elif date_range == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    else:
        start_date = today
        end_date = today
    
    # Get all restaurants and inventories for filters
    all_restaurants = Restaurant.objects.filter(is_active=True)
    all_inventories = Inventory.objects.filter(is_active=True)
    
    # Get current month range
    start_of_month = today.replace(day=1)
    
    # ==================== DAILY RESTAURANT DATA ====================
    restaurant_data = []
    total_restaurant_sales = 0
    total_restaurant_profit = 0
    total_restaurant_orders = 0
    total_restaurant_cost = 0
    total_waste_cost = 0
    
    # Base orders queryset for daily
    base_orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        payment_status='paid'
    )
    
    if restaurant_id:
        base_orders = base_orders.filter(restaurant_id=restaurant_id)
    
    # Get restaurants to display
    if restaurant_id:
        restaurants_to_show = Restaurant.objects.filter(id=restaurant_id, is_active=True)
    else:
        restaurants_to_show = all_restaurants
    
    for restaurant in restaurants_to_show:
        restaurant_orders = base_orders.filter(restaurant=restaurant)
        restaurant_sales = restaurant_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        restaurant_orders_count = restaurant_orders.count()
        
        # Calculate cost
        restaurant_cost = 0
        for order in restaurant_orders:
            for item in order.items.all():
                if item.menu_item.cost:
                    restaurant_cost += item.menu_item.cost * item.quantity
        
        # Calculate waste for this restaurant (daily)
        restaurant_waste = WasteRecord.objects.filter(
            restaurant=restaurant,
            recorded_at__date__gte=start_date,
            recorded_at__date__lte=end_date
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        restaurant_profit = restaurant_sales - restaurant_cost
        
        restaurant_data.append({
            'restaurant': restaurant,
            'sales': restaurant_sales,
            'orders': restaurant_orders_count,
            'cost': restaurant_cost,
            'profit': restaurant_profit,
            'waste': restaurant_waste,
            'margin': (restaurant_profit / restaurant_sales * 100) if restaurant_sales > 0 else 0
        })
        
        total_restaurant_sales += restaurant_sales
        total_restaurant_profit += restaurant_profit
        total_restaurant_orders += restaurant_orders_count
        total_restaurant_cost += restaurant_cost
        total_waste_cost += restaurant_waste
    
    # ==================== MONTHLY RESTAURANT DATA ====================
    monthly_orders_base = Order.objects.filter(
        created_at__date__gte=start_of_month,
        created_at__date__lte=today,
        payment_status='paid'
    )
    
    if restaurant_id:
        monthly_orders_base = monthly_orders_base.filter(restaurant_id=restaurant_id)
    
    monthly_restaurant_data = []
    total_monthly_sales = 0
    total_monthly_orders = 0
    total_monthly_cost = 0
    total_monthly_waste = 0
    
    for restaurant in restaurants_to_show:
        restaurant_orders = monthly_orders_base.filter(restaurant=restaurant)
        restaurant_sales = restaurant_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        restaurant_orders_count = restaurant_orders.count()
        
        # Calculate cost
        restaurant_cost = 0
        for order in restaurant_orders:
            for item in order.items.all():
                if item.menu_item.cost:
                    restaurant_cost += item.menu_item.cost * item.quantity
        
        # Calculate waste for this restaurant (monthly)
        restaurant_waste = WasteRecord.objects.filter(
            restaurant=restaurant,
            recorded_at__date__gte=start_of_month,
            recorded_at__date__lte=today
        ).aggregate(total=Sum('quantity'))['total'] or 0
        
        monthly_restaurant_data.append({
            'restaurant': restaurant,
            'sales': restaurant_sales,
            'orders': restaurant_orders_count,
            'cost': restaurant_cost,
            'waste': restaurant_waste,
        })
        
        total_monthly_sales += restaurant_sales
        total_monthly_orders += restaurant_orders_count
        total_monthly_cost += restaurant_cost
        total_monthly_waste += restaurant_waste
    
    # ==================== INVENTORY DATA ====================
    # Daily inventory cost
    daily_transactions = StockTransaction.objects.filter(
        created_at__date=today
    )
    daily_inventory_cost = daily_transactions.filter(transaction_type='usage').aggregate(total=Sum('total_cost'))['total'] or 0
    daily_purchases = daily_transactions.filter(transaction_type='purchase').aggregate(total=Sum('total_cost'))['total'] or 0
    daily_wastage_cost = daily_transactions.filter(transaction_type='wastage').aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Monthly inventory cost
    monthly_transactions = StockTransaction.objects.filter(
        created_at__date__gte=start_of_month,
        created_at__date__lte=today
    )
    monthly_inventory_cost = monthly_transactions.filter(transaction_type='usage').aggregate(total=Sum('total_cost'))['total'] or 0
    monthly_purchases_total = monthly_transactions.filter(transaction_type='purchase').aggregate(total=Sum('total_cost'))['total'] or 0
    monthly_wastage_cost = monthly_transactions.filter(transaction_type='wastage').aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Total inventory value
    total_inventory_value = 0
    for material in RawMaterial.objects.all():
        total_inventory_value += material.current_stock * material.unit_cost
    
    # Low stock count
    low_stock_count = RawMaterial.objects.filter(current_stock__lte=F('minimum_stock')).count()
    
    # Total materials count
    total_materials_count = RawMaterial.objects.count()
    
    # Pending requests
    pending_requests_count = StockRequest.objects.filter(status='pending').count()
    
    # ==================== MONTHLY MATERIAL USAGE ====================
    monthly_material_usage = []
    materials = RawMaterial.objects.all()
    if inventory_id:
        materials = materials.filter(inventory_id=inventory_id)
    
    for material in materials:
        monthly_usage = StockTransaction.objects.filter(
            raw_material=material,
            transaction_type='usage',
            created_at__date__gte=start_of_month,
            created_at__date__lte=today
        ).aggregate(
            total_qty=Sum('quantity'),
            total_cost=Sum('total_cost')
        )
        
        if monthly_usage['total_qty'] and monthly_usage['total_qty'] > 0:
            monthly_material_usage.append({
                'name': material.name,
                'category_name': material.category.name if material.category else None,
                'unit': material.unit,
                'monthly_quantity': monthly_usage['total_qty'],
                'monthly_cost': monthly_usage['total_cost'] or 0,
                'current_stock': material.current_stock,
                'minimum_stock': material.minimum_stock,
            })
    
    # Sort by monthly cost descending
    monthly_material_usage.sort(key=lambda x: x['monthly_cost'], reverse=True)
    
    # ==================== GENERAL STATISTICS ====================
    total_restaurants = all_restaurants.count()
    total_inventories = all_inventories.count()
    total_employees = Employee.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    total_menu_items = MenuItem.objects.filter(is_available=True).count()
    
    # Recent stock requests
    recent_requests = StockRequest.objects.all().order_by('-requested_at')[:10]
    
    # Prepare date strings
    start_date_str_formatted = start_date.strftime('%Y-%m-%d') if start_date else ''
    end_date_str_formatted = end_date.strftime('%Y-%m-%d') if end_date else ''
    
    context = {
        # Daily restaurant data
        'restaurant_data': restaurant_data,
        'total_restaurant_sales': total_restaurant_sales,
        'total_restaurant_profit': total_restaurant_profit,
        'total_restaurant_orders': total_restaurant_orders,
        'total_restaurant_cost': total_restaurant_cost,
        'total_waste_cost': total_waste_cost,
        
        # Monthly restaurant data
        'monthly_restaurant_data': monthly_restaurant_data,
        'total_monthly_sales': total_monthly_sales,
        'total_monthly_orders': total_monthly_orders,
        'total_monthly_cost': total_monthly_cost,
        'total_monthly_waste': total_monthly_waste,
        
        # Inventory data
        'daily_inventory_cost': daily_inventory_cost,
        'daily_purchases': daily_purchases,
        'daily_wastage_cost': daily_wastage_cost,
        'monthly_inventory_cost': monthly_inventory_cost,
        'monthly_purchases_total': monthly_purchases_total,
        'monthly_wastage_cost': monthly_wastage_cost,
        'total_inventory_value': total_inventory_value,
        'low_stock_count': low_stock_count,
        'total_materials_count': total_materials_count,
        'pending_requests_count': pending_requests_count,
        
        # Monthly material usage
        'monthly_material_usage': monthly_material_usage,
        
        # General stats
        'total_restaurants': total_restaurants,
        'total_inventories': total_inventories,
        'total_employees': total_employees,
        'total_users': total_users,
        'total_menu_items': total_menu_items,
        
        # Filter data
        'restaurants': all_restaurants,
        'inventories': all_inventories,
        'selected_restaurant': restaurant_id,
        'selected_inventory': inventory_id,
        'date_range': date_range,
        'start_date': start_date_str_formatted,
        'end_date': end_date_str_formatted,
        'view_type': view_type,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'common/admin_dashboard.html', context)