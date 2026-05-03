# apps/reports/views.py
from django.contrib import messages  # Fixed import (remove pyexpat.errors import)
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
from apps.accounts.models import Employee, User
from apps.orders.models import Order, OrderItem, WasteRecord
from apps.restaurant.models import Recipe, Restaurant, MenuItem
from apps.inventory.models import Inventory, RawMaterial, StockTransaction, StockRequest

@login_required
def sales_report(request):
    """Sales report - all roles with appropriate filters"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    restaurant_id = request.GET.get('restaurant')
    
    orders = Order.objects.filter(payment_status='paid')
    
    # Apply filters
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    # Restaurant filter based on role
    if request.user.role == 'admin':
        if restaurant_id:
            orders = orders.filter(restaurant_id=restaurant_id)
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.role in ['staff', 'manager']:
        if request.user.restaurant:
            orders = orders.filter(restaurant=request.user.restaurant)
        restaurants = [request.user.restaurant] if request.user.restaurant else []
    else:
        restaurants = []
    
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = orders.count()
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    daily_sales = orders.extra({'date': "DATE(created_at)"}).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-date')
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'daily_sales': daily_sales,
        'start_date': start_date,
        'end_date': end_date,
        'restaurants': restaurants,
    }
    return render(request, 'reports/sales_report.html', context)

@login_required
def profit_report(request):
    """Profit report - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can view profit reports.')
        return redirect('common:dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    orders = Order.objects.filter(payment_status='paid')
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Calculate cost
    total_cost = 0
    for order in orders:
        for item in order.items.all():
            if item.menu_item.has_recipe:
                recipes = Recipe.objects.filter(menu_item=item.menu_item)
                for recipe in recipes:
                    total_cost += recipe.quantity_required * recipe.raw_material.unit_cost * item.quantity
    
    total_profit = total_revenue - total_cost
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    context = {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/profit_report.html', context)

@login_required
def wastage_report(request):
    """Wastage report - all roles"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if request.user.role == 'admin':
        wastes = WasteRecord.objects.all()
    elif request.user.role in ['staff', 'manager']:
        if not request.user.restaurant:
            messages.error(request, 'No restaurant assigned')
            return redirect('common:dashboard')
        wastes = WasteRecord.objects.filter(restaurant=request.user.restaurant)
    else:
        wastes = WasteRecord.objects.filter(recorded_by=request.user)
    
    if start_date:
        wastes = wastes.filter(recorded_at__date__gte=start_date)
    if end_date:
        wastes = wastes.filter(recorded_at__date__lte=end_date)
    
    total_wastage_cost = 0
    for waste in wastes:
        if waste.menu_item.has_recipe:
            recipes = Recipe.objects.filter(menu_item=waste.menu_item)
            for recipe in recipes:
                total_wastage_cost += recipe.quantity_required * recipe.raw_material.unit_cost * waste.quantity
    
    wastage_by_item = wastes.values('menu_item__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')
    
    context = {
        'total_wastage_cost': total_wastage_cost,
        'wastage_by_item': wastage_by_item,
        'total_wastes': wastes.count(),
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/wastage_report.html', context)

@login_required
def inventory_report(request):
    """Inventory report - admin and store"""
    # Fix: Check for both 'admin' and 'superadmin' roles
    if request.user.role == 'admin' or request.user.role == 'superadmin' or request.user.is_superuser:
        materials = RawMaterial.objects.all()
        inventories = Inventory.objects.filter(is_active=True)
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
        inventories = [request.user.inventory]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    total_value = 0
    for material in materials:
        total_value += material.current_stock * material.unit_cost
    
    low_stock_items = materials.filter(current_stock__lte=F('minimum_stock'))
    
    # Calculate stock health
    total_items = materials.count()
    healthy_count = total_items - low_stock_items.count()
    
    context = {
        'total_materials': total_items,
        'total_value': total_value,
        'low_stock_count': low_stock_items.count(),
        'low_stock_items': low_stock_items,
        'healthy_count': healthy_count,
        'materials': materials,
        'inventories': inventories,
        'user_role': request.user.role,
    }
    return render(request, 'reports/inventory_report.html', context)

@login_required
def business_summary(request):
    """Business summary - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can view business summary.')
        return redirect('common:dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = timezone.now().replace(day=1).date()
    if not end_date:
        end_date = timezone.now().date()
    
    total_restaurants = Restaurant.objects.filter(is_active=True).count()
    total_employees = Employee.objects.filter(is_active=True).count()
    total_users = User.objects.filter(is_active=True).count()
    
    all_orders = Order.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
        payment_status='paid'
    )
    
    total_revenue = all_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = all_orders.count()
    
    # Calculate cost
    total_cost = 0
    for order in all_orders:
        for item in order.items.all():
            if item.menu_item.has_recipe:
                recipes = Recipe.objects.filter(menu_item=item.menu_item)
                for recipe in recipes:
                    total_cost += recipe.quantity_required * recipe.raw_material.unit_cost * item.quantity
    
    # Wastage cost
    all_wastage = WasteRecord.objects.filter(
        recorded_at__date__gte=start_date,
        recorded_at__date__lte=end_date
    )
    wastage_cost = 0
    for waste in all_wastage:
        if waste.menu_item.has_recipe:
            recipes = Recipe.objects.filter(menu_item=waste.menu_item)
            for recipe in recipes:
                wastage_cost += recipe.quantity_required * recipe.raw_material.unit_cost * waste.quantity
    
    total_profit = total_revenue - total_cost - wastage_cost
    
    # Restaurant breakdown
    restaurant_breakdown = []
    for restaurant in Restaurant.objects.filter(is_active=True):
        restaurant_orders = all_orders.filter(restaurant=restaurant)
        restaurant_revenue = restaurant_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        restaurant_cost = 0
        for order in restaurant_orders:
            for item in order.items.all():
                if item.menu_item.has_recipe:
                    recipes = Recipe.objects.filter(menu_item=item.menu_item)
                    for recipe in recipes:
                        restaurant_cost += recipe.quantity_required * recipe.raw_material.unit_cost * item.quantity
        
        restaurant_profit = restaurant_revenue - restaurant_cost
        
        restaurant_breakdown.append({
            'restaurant': restaurant,
            'revenue': restaurant_revenue,
            'orders': restaurant_orders.count(),
            'profit': restaurant_profit,
            'margin': (restaurant_profit / restaurant_revenue * 100) if restaurant_revenue > 0 else 0
        })
    
    # Top products
    top_products = OrderItem.objects.filter(
        order__created_at__date__gte=start_date,
        order__created_at__date__lte=end_date
    ).values('menu_item__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:10]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_restaurants': total_restaurants,
        'total_employees': total_employees,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_cost': total_cost,
        'wastage_cost': wastage_cost,
        'total_profit': total_profit,
        'profit_margin': (total_profit / total_revenue * 100) if total_revenue > 0 else 0,
        'avg_order_value': total_revenue / total_orders if total_orders > 0 else 0,
        'restaurant_breakdown': restaurant_breakdown,
        'top_products': top_products,
    }
    
    return render(request, 'reports/business_summary.html', context)


@login_required
def export_report(request, report_type):
    """Export report to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'sales':
        writer.writerow(['Order ID', 'Date', 'Restaurant', 'Total Amount', 'Status'])
        orders = Order.objects.filter(payment_status='paid')
        for order in orders:
            writer.writerow([order.order_number, order.created_at.date(), order.restaurant.name, order.total_amount, order.status])
    
    elif report_type == 'wastage':
        writer.writerow(['Date', 'Restaurant', 'Menu Item', 'Quantity', 'Reason'])
        wastes = WasteRecord.objects.all()
        for waste in wastes:
            writer.writerow([waste.recorded_at.date(), waste.restaurant.name, waste.menu_item.name, waste.quantity, waste.reason])
    
    return response


@login_required
def daily_sales_report(request):
    """Daily sales report"""
    date_str = request.GET.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = timezone.now().date()
    else:
        date = timezone.now().date()
    
    if request.user.role == 'admin':
        orders = Order.objects.filter(created_at__date=date, payment_status='paid')
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.role in ['staff', 'manager']:
        if not request.user.restaurant:
            messages.error(request, 'No restaurant assigned')
            return redirect('common:dashboard')
        orders = Order.objects.filter(restaurant=request.user.restaurant, created_at__date=date, payment_status='paid')
        restaurants = [request.user.restaurant]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = orders.count()
    
    # Hourly breakdown
    hourly_breakdown = orders.extra({'hour': "EXTRACT(hour FROM created_at)"}).values('hour').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('hour')
    
    context = {
        'orders': orders,
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order': total_sales / total_orders if total_orders > 0 else 0,
        'date': date,
        'restaurants': restaurants,
        'hourly_breakdown': hourly_breakdown,
    }
    return render(request, 'reports/daily_sales.html', context)

@login_required
def monthly_sales_report(request):
    """Monthly sales report"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    if request.user.role == 'admin':
        orders = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date,
            payment_status='paid'
        )
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.role in ['staff', 'manager']:
        if not request.user.restaurant:
            messages.error(request, 'No restaurant assigned')
            return redirect('common:dashboard')
        orders = Order.objects.filter(
            restaurant=request.user.restaurant,
            created_at__gte=start_date,
            created_at__lt=end_date,
            payment_status='paid'
        )
        restaurants = [request.user.restaurant]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = orders.count()
    
    # Daily breakdown
    daily_breakdown = orders.extra({'day': "EXTRACT(day FROM created_at)"}).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    context = {
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order': total_sales / total_orders if total_orders > 0 else 0,
        'year': year,
        'month': month,
        'month_name': start_date.strftime('%B'),
        'daily_breakdown': daily_breakdown,
        'restaurants': restaurants,
    }
    return render(request, 'reports/monthly_sales.html', context)

@login_required
def profit_loss_report(request):
    """Profit & Loss report - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can view profit/loss reports.')
        return redirect('common:dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    orders = Order.objects.filter(payment_status='paid')
    
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Calculate cost
    total_cost = 0
    for order in orders:
        for item in order.items.all():
            if item.menu_item.has_recipe:
                recipes = Recipe.objects.filter(menu_item=item.menu_item)
                for recipe in recipes:
                    total_cost += recipe.quantity_required * recipe.raw_material.unit_cost * item.quantity
    
    # Calculate wastage cost
    wastes = WasteRecord.objects.all()
    if start_date:
        wastes = wastes.filter(recorded_at__date__gte=start_date)
    if end_date:
        wastes = wastes.filter(recorded_at__date__lte=end_date)
    
    wastage_cost = 0
    for waste in wastes:
        if waste.menu_item.has_recipe:
            recipes = Recipe.objects.filter(menu_item=waste.menu_item)
            for recipe in recipes:
                wastage_cost += recipe.quantity_required * recipe.raw_material.unit_cost * waste.quantity
    
    total_profit = total_revenue - total_cost - wastage_cost
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    context = {
        'total_revenue': total_revenue,
        'total_cost': total_cost,
        'wastage_cost': wastage_cost,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/profit_loss.html', context)

@login_required
def daily_wastage_report(request):
    """Daily wastage report"""
    date_str = request.GET.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date = timezone.now().date()
    else:
        date = timezone.now().date()
    
    if request.user.role == 'admin':
        wastes = WasteRecord.objects.filter(recorded_at__date=date)
        restaurants = Restaurant.objects.filter(is_active=True)
    elif request.user.role in ['staff', 'manager']:
        if not request.user.restaurant:
            messages.error(request, 'No restaurant assigned')
            return redirect('common:dashboard')
        wastes = WasteRecord.objects.filter(restaurant=request.user.restaurant, recorded_at__date=date)
        restaurants = [request.user.restaurant]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    total_cost = 0
    for waste in wastes:
        if waste.menu_item.has_recipe:
            recipes = Recipe.objects.filter(menu_item=waste.menu_item)
            for recipe in recipes:
                total_cost += recipe.quantity_required * recipe.raw_material.unit_cost * waste.quantity
    
    context = {
        'wastes': wastes,
        'total_wastes': wastes.count(),
        'total_cost': total_cost,
        'date': date,
        'restaurants': restaurants,
    }
    return render(request, 'reports/daily_wastage.html', context)

@login_required
def stock_value_report(request):
    """Stock value report - admin and store"""
    if request.user.role == 'admin':
        materials = RawMaterial.objects.all()
        inventories = Inventory.objects.filter(is_active=True)
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
        inventories = [request.user.inventory]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    total_value = 0
    for material in materials:
        total_value += material.current_stock * material.unit_cost
    
    # Group by category
    by_category = materials.values('category').annotate(
        total_value=Sum(F('current_stock') * F('unit_cost')),
        total_quantity=Sum('current_stock')
    ).order_by('-total_value')
    
    # Group by inventory
    by_inventory = materials.values('inventory__name').annotate(
        total_value=Sum(F('current_stock') * F('unit_cost')),
        total_items=Count('id')
    )
    
    context = {
        'materials': materials,
        'total_value': total_value,
        'total_items': materials.count(),
        'by_category': by_category,
        'by_inventory': by_inventory,
        'inventories': inventories,
    }
    return render(request, 'reports/stock_value.html', context)

@login_required
def reports_dashboard(request):
    """Reports dashboard - main reports landing page"""
    context = {
        'user': request.user,
        'is_admin': request.user.role == 'admin',
        'is_staff': request.user.role in ['staff', 'manager'],
        'is_store': request.user.role == 'store',
    }
    return render(request, 'reports/reports_dashboard.html', context)


@login_required
def advanced_report(request):
    """Advanced report with multiple filters - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can access advanced reports.')
        return redirect('common:dashboard')
    
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    restaurant_id = request.GET.get('restaurant')
    category = request.GET.get('category')
    min_amount = request.GET.get('min_amount')
    max_amount = request.GET.get('max_amount')
    status = request.GET.get('status')
    payment_status = request.GET.get('payment_status')
    
    orders = Order.objects.all()
    
    # Apply filters
    if start_date:
        orders = orders.filter(created_at__date__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__date__lte=end_date)
    if restaurant_id:
        orders = orders.filter(restaurant_id=restaurant_id)
    if min_amount:
        orders = orders.filter(total_amount__gte=min_amount)
    if max_amount:
        orders = orders.filter(total_amount__lte=max_amount)
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = orders.count()
    avg_order_value = total_sales / total_orders if total_orders > 0 else 0
    
    # Group by restaurant
    by_restaurant = orders.values('restaurant__name').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-total')
    
    # Group by date
    by_date = orders.extra({'date': "DATE(created_at)"}).values('date').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('-date')
    
    # Group by status
    by_status = orders.values('status').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    restaurants = Restaurant.objects.filter(is_active=True)
    
    # Order items breakdown
    top_items = OrderItem.objects.filter(
        order__in=orders
    ).values('menu_item__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_revenue')[:10]
    
    context = {
        'orders': orders[:100],  # Limit to 100 for display
        'total_sales': total_sales,
        'total_orders': total_orders,
        'avg_order_value': avg_order_value,
        'by_restaurant': by_restaurant,
        'by_date': by_date,
        'by_status': by_status,
        'top_items': top_items,
        'restaurants': restaurants,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'restaurant_id': restaurant_id,
            'category': category,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'status': status,
            'payment_status': payment_status,
        }
    }
    
    return render(request, 'reports/advanced_report.html', context)