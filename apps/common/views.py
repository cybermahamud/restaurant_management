# apps/common/views.py - Complete fixed version
import json

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
    
    # Set date range - FIXED: Proper error handling
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
            # If parsing fails, use today
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
    
    # ==================== RESTAURANT VIEW ====================
    restaurant_data = []
    total_restaurant_sales = 0
    total_restaurant_profit = 0
    total_restaurant_orders = 0
    
    # Base orders queryset
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
        
        # Calculate profit
        restaurant_cost = 0
        for order in restaurant_orders:
            for item in order.items.all():
                if item.menu_item.cost:
                    restaurant_cost += item.menu_item.cost * item.quantity
        
        restaurant_profit = restaurant_sales - restaurant_cost
        
        restaurant_data.append({
            'restaurant': restaurant,
            'sales': restaurant_sales,
            'orders': restaurant_orders_count,
            'cost': restaurant_cost,
            'profit': restaurant_profit,
            'margin': (restaurant_profit / restaurant_sales * 100) if restaurant_sales > 0 else 0
        })
        
        total_restaurant_sales += restaurant_sales
        total_restaurant_profit += restaurant_profit
        total_restaurant_orders += restaurant_orders_count
    
    # Calculate average order value safely
    avg_order_value = 0
    if total_restaurant_orders > 0:
        avg_order_value = total_restaurant_sales / total_restaurant_orders
    
    # Item-wise sales summary
    item_sales = OrderItem.objects.filter(
        order__in=base_orders
    ).values('menu_item__name', 'menu_item__category__name').annotate(
        quantity_sold=Sum('quantity'),
        total_revenue=Sum('total_price'),
        total_cost=Sum(F('quantity') * F('menu_item__cost'))
    ).order_by('-total_revenue')[:20]
    
    for item in item_sales:
        item['profit'] = item['total_revenue'] - (item['total_cost'] or 0)
        item['margin'] = (item['profit'] / item['total_revenue'] * 100) if item['total_revenue'] > 0 else 0
    
    # Daily sales breakdown - FIXED: Use proper date extraction
    from django.db.models.functions import TruncDate
    daily_sales = base_orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('date')
    
    # Top selling items
    top_items = OrderItem.objects.filter(
        order__in=base_orders
    ).values('menu_item__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:10]
    
    # ==================== INVENTORY VIEW ====================
    inventory_data = []
    total_inventory_value = 0
    total_purchases = 0
    total_usage = 0
    total_wastage = 0
    
    # Base stock transactions
    base_transactions = StockTransaction.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )
    
    if inventory_id:
        base_transactions = base_transactions.filter(raw_material__inventory_id=inventory_id)
    
    # Get inventories to display
    if inventory_id:
        inventories_to_show = Inventory.objects.filter(id=inventory_id, is_active=True)
    else:
        inventories_to_show = all_inventories
    
    for inventory in inventories_to_show:
        inv_transactions = base_transactions.filter(raw_material__inventory=inventory)
        
        purchases = inv_transactions.filter(transaction_type='purchase').aggregate(total=Sum('total_cost'))['total'] or 0
        usage = inv_transactions.filter(transaction_type='usage').aggregate(total=Sum('total_cost'))['total'] or 0
        wastage = inv_transactions.filter(transaction_type='wastage').aggregate(total=Sum('total_cost'))['total'] or 0
        
        # Current inventory value
        inv_value = RawMaterial.objects.filter(inventory=inventory).aggregate(
            total=Sum(F('current_stock') * F('unit_cost'))
        )['total'] or 0
        
        inventory_data.append({
            'inventory': inventory,
            'purchases': purchases,
            'usage': usage,
            'wastage': wastage,
            'current_value': inv_value,
            'material_count': RawMaterial.objects.filter(inventory=inventory).count()
        })
        
        total_inventory_value += inv_value
        total_purchases += purchases
        total_usage += usage
        total_wastage += wastage
    
    # Top used materials
    top_materials = base_transactions.filter(transaction_type='usage').values(
        'raw_material__name', 'raw_material__unit'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_cost')
    ).order_by('-total_cost')[:10]
    
    # Low stock items
    low_stock_items = RawMaterial.objects.filter(current_stock__lte=F('minimum_stock'))
    if inventory_id:
        low_stock_items = low_stock_items.filter(inventory_id=inventory_id)
    low_stock_items = low_stock_items[:10]
    low_stock_count = RawMaterial.objects.filter(current_stock__lte=F('minimum_stock')).count()
    
    # Monthly purchase trend - FIXED: Use proper month extraction
    from django.db.models.functions import TruncMonth
    monthly_purchases = base_transactions.filter(
        transaction_type='purchase'
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('total_cost')
    ).order_by('-month')[:6]
    
    # Format month for display
    for item in monthly_purchases:
        if item['month']:
            item['month_str'] = item['month'].strftime('%b %Y')
    
    # ==================== STOCK REQUESTS ====================
    pending_requests = StockRequest.objects.filter(status='pending')
    if restaurant_id:
        pending_requests = pending_requests.filter(restaurant_id=restaurant_id)
    pending_requests_count = pending_requests.count()
    
    recent_requests = StockRequest.objects.all().order_by('-requested_at')[:10]
    if restaurant_id:
        recent_requests = recent_requests.filter(restaurant_id=restaurant_id)
    
    # ==================== GENERAL STATISTICS ====================
    total_restaurants = all_restaurants.count()
    total_inventories = all_inventories.count()
    total_employees = Employee.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    total_menu_items = MenuItem.objects.filter(is_available=True).count()
    
    # Prepare date strings for template - FIXED: Convert to strings safely
    start_date_str_formatted = start_date.strftime('%Y-%m-%d') if start_date else ''
    end_date_str_formatted = end_date.strftime('%Y-%m-%d') if end_date else ''
    
    context = {
        'restaurant_data': restaurant_data,
        'total_restaurant_sales': total_restaurant_sales,
        'total_restaurant_profit': total_restaurant_profit,
        'total_restaurant_orders': total_restaurant_orders,
        'avg_order_value': avg_order_value,
        'item_sales': item_sales,
        'daily_sales': daily_sales,
        'top_items': top_items,
        'inventory_data': inventory_data,
        'total_inventory_value': total_inventory_value,
        'total_purchases': total_purchases,
        'total_usage': total_usage,
        'total_wastage': total_wastage,
        'top_materials': top_materials,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_count,
        'monthly_purchases': monthly_purchases,
        'pending_requests_count': pending_requests_count,
        'recent_requests': recent_requests,
        'total_restaurants': total_restaurants,
        'total_inventories': total_inventories,
        'total_employees': total_employees,
        'total_users': total_users,
        'total_menu_items': total_menu_items,
        'restaurants': all_restaurants,
        'inventories': all_inventories,
        'selected_restaurant': restaurant_id,
        'selected_inventory': inventory_id,
        'date_range': date_range,
        'start_date': start_date_str_formatted,  # Send as string
        'end_date': end_date_str_formatted,      # Send as string
        'view_type': view_type,
    }
    
    return render(request, 'common/admin_dashboard.html', context)


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