# apps/orders/views.py
from datetime import timedelta
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from .models import Order, OrderItem, Payment, WasteRecord, KitchenPrint
from apps.restaurant.models import MenuCategory, Restaurant, Table, MenuItem, SetMenu, SetMenuItem, Recipe
from apps.inventory.models import StockRequest, StockTransaction
from .forms import OrderForm, PaymentForm, WasteForm

from .models import Order, OrderItem, Payment, KitchenPrint
from apps.restaurant.models import Table, MenuItem, MenuCategory

@login_required
def order_list(request):
    """Order list page with active/completed toggle"""
    # Get filter parameter
    show = request.GET.get('show', 'active')
    
    # Get orders based on user role
    if request.user.is_superuser or request.user.role == 'admin':
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(restaurant=request.user.restaurant)
    
    # Filter based on show parameter
    if show == 'active':
        orders = orders.exclude(status__in=['completed', 'cancelled'])
    elif show == 'completed':
        orders = orders.filter(status='completed')
    elif show == 'cancelled':
        orders = orders.filter(status='cancelled')
    
    orders = orders.order_by('-created_at')
    
    # Get counts for badges
    active_count = Order.objects.exclude(status__in=['completed', 'cancelled']).count()
    completed_count = Order.objects.filter(status='completed').count()
    cancelled_count = Order.objects.filter(status='cancelled').count()
    
    context = {
        'orders': orders,
        'show': show,
        'active_count': active_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def take_order(request):
    """Take new order page with stock information"""
    # Get restaurant
    if request.user.is_superuser or request.user.role == 'admin':
        restaurant = Restaurant.objects.first()
    else:
        restaurant = request.user.restaurant
    
    if not restaurant:
        messages.error(request, 'No restaurant found')
        return redirect('common:dashboard')
    
    tables = Table.objects.filter(restaurant=restaurant, status='available')
    menu_items = MenuItem.objects.filter(is_available=True)
    categories = MenuCategory.objects.filter(is_active=True)
    
    # Prepare menu items with stock info
    menu_items_with_stock = []
    for item in menu_items:
        menu_items_with_stock.append({
            'id': str(item.id),
            'name': item.name,
            'description': item.description,
            'price': float(item.price),
            'category_id': str(item.category.id) if item.category else None,
            'quantity': item.quantity,
            'reorder_level': item.reorder_level,
            'is_low_stock': item.is_low_stock,
            'is_available': item.is_available and item.quantity > 0,
            'max_order': item.quantity,
        })
    
    context = {
        'tables': tables,
        'menu_items': menu_items_with_stock,
        'categories': categories,
        'restaurant': restaurant,
    }
    return render(request, 'orders/take_order.html', context)

@login_required
def create_order(request):
    """Create new order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    restaurant = request.user.restaurant if request.user.restaurant else Restaurant.objects.first()
    
    table_id = request.POST.get('table_id')
    order_type = request.POST.get('order_type')
    items = json.loads(request.POST.get('items', '[]'))
    quantities = json.loads(request.POST.get('quantities', '[]'))
    discount_amount = Decimal(request.POST.get('discount_amount', 0))
    discount_type = request.POST.get('discount_type', 'percentage')
    
    # Create order
    order = Order.objects.create(
        order_number=f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}",
        restaurant=restaurant,
        staff=request.user,
        order_type=order_type,
        discount_amount=discount_amount,
        discount_type=discount_type,
        status='pending',
        payment_status='pending'
    )
    
    # Set table
    if table_id:
        table = get_object_or_404(Table, id=table_id)
        order.table = table
        table.status = 'occupied'
        table.save()
    
    # Add items and reduce stock
    for item_id, quantity in zip(items, quantities):
        menu_item = get_object_or_404(MenuItem, id=item_id)
        
        # Check if enough stock
        if menu_item.quantity < int(quantity):
            return JsonResponse({'error': f'Insufficient stock for {menu_item.name}'}, status=400)
        
        # Reduce stock
        menu_item.quantity -= int(quantity)
        menu_item.save()
        
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=int(quantity),
            unit_price=menu_item.price
        )
    
    # Calculate totals
    order.subtotal = order.items.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    if discount_type == 'percentage':
        discount = (order.subtotal * discount_amount) / 100
    else:
        discount = discount_amount
    
    order.tax_amount = (order.subtotal - discount) * Decimal('0.05')
    order.total_amount = order.subtotal - discount + order.tax_amount
    order.save()
    
    return JsonResponse({'success': True, 'message': f'Order {order.order_number} created', 'order_id': str(order.id)})


@login_required
def edit_order(request, order_id):
    """Edit existing order - load order data"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check permission
    if not (request.user.is_superuser or request.user.role == 'admin'):
        if order.restaurant != request.user.restaurant:
            messages.error(request, 'Access denied')
            return redirect('orders:order_list')
    
    # Get data for the page
    restaurant = order.restaurant
    tables = Table.objects.filter(restaurant=restaurant)
    menu_items = MenuItem.objects.filter(is_available=True)
    categories = MenuCategory.objects.filter(is_active=True)
    
    # Prepare order items for JavaScript
    order_items = []
    for item in order.items.all():
        order_items.append({
            'id': str(item.menu_item.id),
            'name': item.menu_item.name,
            'price': float(item.unit_price),
            'quantity': float(item.quantity),
        })
    
    context = {
        'order': order,
        'tables': tables,
        'menu_items': menu_items,
        'categories': categories,
        'order_items_json': json.dumps(order_items),
    }
    return render(request, 'orders/edit_order.html', context)

@login_required
def delete_order(request, order_id):
    """Permanently delete order - admin only"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    # Only admin or superadmin can delete orders
    if not (request.user.is_superuser or request.user.role == 'admin'):
        return JsonResponse({'error': 'Access denied. Only administrators can delete orders'}, status=403)
    
    order = get_object_or_404(Order, id=order_id)
    order_number = order.order_number
    
    # Release table if occupied
    if order.table:
        order.table.status = 'available'
        order.table.save()
    
    # Delete the order (cascades to order items, payments, etc.)
    order.delete()
    
    return JsonResponse({'success': True, 'message': f'Order {order_number} deleted successfully'})

@login_required
def cancel_order(request, order_id):
    """Cancel order - staff and above - Adds stock back to inventory"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    
    # Check permission
    if not (request.user.is_superuser or request.user.role == 'admin'):
        if request.user.role in ['staff', 'manager']:
            if order.restaurant != request.user.restaurant:
                return JsonResponse({'error': 'Access denied'}, status=403)
        else:
            return JsonResponse({'error': 'Access denied'}, status=403)
    
    if order.status == 'completed':
        return JsonResponse({'error': 'Cannot cancel completed order'}, status=400)
    
    if order.status == 'cancelled':
        return JsonResponse({'error': 'Order is already cancelled'}, status=400)
    
    # ADD STOCK BACK FOR EACH ITEM
    for item in order.items.all():
        menu_item = item.menu_item
        # Add the quantity back to stock
        menu_item.quantity += int(item.quantity)
        menu_item.save()
        
        # Optional: Record a stock transaction for the return
        # Uncomment if you want to track this in stock transactions
        # from apps.inventory.models import StockTransaction
        # StockTransaction.objects.create(
        #     raw_material=None,  # You would need to map to raw materials
        #     transaction_type='adjustment',
        #     quantity=item.quantity,
        #     total_cost=0,
        #     reference_number=f"CANCEL-{order.order_number}",
        #     notes=f"Stock returned from cancelled order {order.order_number}",
        #     created_by=request.user
        # )
    
    order.status = 'cancelled'
    order.save()
    
    # Release table
    if order.table:
        order.table.status = 'available'
        order.table.save()
    
    return JsonResponse({'success': True, 'message': f'Order {order.order_number} cancelled successfully. Stock has been returned.'})

@login_required
def update_order(request, order_id):
    """Update existing order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    
    table_id = request.POST.get('table_id')
    order_type = request.POST.get('order_type')
    items = json.loads(request.POST.get('items', '[]'))
    quantities = json.loads(request.POST.get('quantities', '[]'))
    discount_amount = Decimal(request.POST.get('discount_amount', 0))
    discount_type = request.POST.get('discount_type', 'percentage')
    
    # Update table
    if table_id:
        new_table = get_object_or_404(Table, id=table_id)
        if order.table and order.table != new_table:
            order.table.status = 'available'
            order.table.save()
        order.table = new_table
        new_table.status = 'occupied'
        new_table.save()
    
    order.order_type = order_type
    order.discount_amount = discount_amount
    order.discount_type = discount_type
    
    # Clear and add items
    order.items.all().delete()
    for item_id, quantity in zip(items, quantities):
        menu_item = get_object_or_404(MenuItem, id=item_id)
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=int(quantity),
            unit_price=menu_item.price
        )
    
    # Recalculate totals
    order.subtotal = order.items.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    if discount_type == 'percentage':
        discount = (order.subtotal * discount_amount) / 100
    else:
        discount = discount_amount
    
    order.tax_amount = (order.subtotal - discount) * Decimal('0.05')
    order.total_amount = order.subtotal - discount + order.tax_amount
    order.save()
    
    return JsonResponse({'success': True, 'message': 'Order updated'})


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    status = request.POST.get('status')
    
    order.status = status
    order.save()
    
    # Release table if completed or cancelled
    if status in ['completed', 'cancelled'] and order.table:
        order.table.status = 'available'
        order.table.save()
    
    return JsonResponse({'success': True, 'message': f'Status updated to {status}'})


@login_required
def add_item_to_order(request, order_id):
    """Add item to existing order"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    
    menu_item = get_object_or_404(MenuItem, id=item_id)
    
    # Check if item already exists
    existing_item = order.items.filter(menu_item=menu_item).first()
    if existing_item:
        existing_item.quantity += quantity
        existing_item.save()
    else:
        OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            unit_price=menu_item.price
        )
    
    # Recalculate totals
    order.subtotal = order.items.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    if order.discount_type == 'percentage':
        discount = (order.subtotal * order.discount_amount) / 100
    else:
        discount = order.discount_amount
    
    order.tax_amount = (order.subtotal - discount) * Decimal('0.05')
    order.total_amount = order.subtotal - discount + order.tax_amount
    order.save()
    
    return JsonResponse({'success': True, 'message': 'Item added'})


@login_required
def kitchen_print(request, order_id):
    """Print kitchen order"""
    order = get_object_or_404(Order, id=order_id)
    
    # Record print
    KitchenPrint.objects.create(order=order, printed_by=request.user)
    
    # Update order status to preparing if pending
    if order.status == 'pending':
        order.status = 'preparing'
        order.save()
    
    return render(request, 'orders/kitchen_print.html', {'order': order})


@login_required
def payment_page(request, order_id):
    """Payment page"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/payment_page.html', {'order': order})


@login_required
def process_payment(request, order_id):
    """Process payment"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    order = get_object_or_404(Order, id=order_id)
    received_amount = Decimal(request.POST.get('received_amount', 0))
    payment_method = request.POST.get('payment_method')
    
    change_amount = received_amount - order.total_amount
    
    Payment.objects.create(
        order=order,
        amount=order.total_amount,
        payment_method=payment_method,
        received_amount=received_amount,
        change_amount=change_amount if change_amount > 0 else 0,
        received_by=request.user
    )
    
    order.payment_status = 'paid'
    order.save()
    
    # Release table
    if order.table:
        order.table.status = 'available'
        order.table.save()
    
    return JsonResponse({'success': True, 'message': 'Payment completed'})


@login_required
def print_bill(request, order_id):
    """Print bill"""
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'orders/bill_print.html', {'order': order})


@login_required
def record_waste(request):
    """Record waste - staff, manager, admin"""
    if request.user.role not in ['staff', 'manager', 'admin']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Determine restaurant
    if request.user.role == 'admin':
        restaurant = request.GET.get('restaurant')
        if restaurant:
            restaurant = get_object_or_404(Restaurant, id=restaurant)
        else:
            restaurant = Restaurant.objects.first()
    else:
        restaurant = request.user.restaurant
    
    if not restaurant:
        messages.error(request, 'No restaurant found')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = WasteForm(request.POST)
        if form.is_valid():
            waste = form.save(commit=False)
            waste.restaurant = restaurant
            waste.recorded_by = request.user
            waste.save()
            
            # Deduct stock
            if waste.menu_item.has_recipe:
                recipes = Recipe.objects.filter(menu_item=waste.menu_item)
                for recipe in recipes:
                    required_qty = recipe.quantity_required * waste.quantity
                    recipe.raw_material.current_stock -= required_qty
                    recipe.raw_material.save()
                    
                    StockTransaction.objects.create(
                        raw_material=recipe.raw_material,
                        transaction_type='wastage',
                        quantity=required_qty,
                        unit_cost=recipe.raw_material.unit_cost,
                        reference_number=f"WASTE-{waste.id}",
                        created_by=request.user
                    )
            
            messages.success(request, 'Waste recorded successfully')
            return redirect('orders:waste_list')
    else:
        form = WasteForm()
    
    return render(request, 'orders/record_waste.html', {'form': form})

@login_required
def waste_list(request):
    """List waste records - based on role"""
    if request.user.role == 'admin':
        wastes = WasteRecord.objects.all()
    elif request.user.role in ['staff', 'manager']:
        if not request.user.restaurant:
            messages.error(request, 'No restaurant assigned')
            return redirect('common:dashboard')
        wastes = WasteRecord.objects.filter(restaurant=request.user.restaurant)
    else:
        wastes = WasteRecord.objects.filter(recorded_by=request.user)
    
    paginator = Paginator(wastes, 20)
    page = request.GET.get('page')
    wastes = paginator.get_page(page)
    
    return render(request, 'orders/waste_list.html', {'wastes': wastes})

