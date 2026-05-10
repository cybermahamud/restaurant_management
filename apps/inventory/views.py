# apps/inventory/views.py
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q, F
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    RawMaterial, RawMaterialCategory, Inventory, StockTransaction, StockRequest,
    DailyStockRequest, DailyRequestItem, ProductionBatch, DispatchRecord
)
from .forms import (
    RawMaterialForm, RawMaterialCategoryForm, InventoryForm, AddStockForm, UpdateStockForm
)
from apps.restaurant.models import MenuItem, Recipe, Restaurant


# ==================== Helper Functions ====================

def has_inventory_access(user):
    """Check if user can access inventory management"""
    return user.role in ['admin', 'superadmin', 'store']


# ==================== Inventory Management ====================

@login_required
def inventory_list(request):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventories = Inventory.objects.all()
    return render(request, 'inventory/inventory_list.html', {'inventories': inventories})


@login_required
def create_inventory(request):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = InventoryForm(request.POST)
        if form.is_valid():
            inventory = form.save()
            messages.success(request, f'Inventory "{inventory.name}" created')
            return redirect('inventory:inventory_list')
    else:
        form = InventoryForm()
    
    return render(request, 'inventory/inventory_form.html', {'form': form, 'title': 'Create Inventory'})


@login_required
def edit_inventory(request, pk):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventory = get_object_or_404(Inventory, id=pk)
    
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory updated')
            return redirect('inventory:inventory_list')
    else:
        form = InventoryForm(instance=inventory)
    
    return render(request, 'inventory/inventory_form.html', {'form': form, 'title': 'Edit Inventory'})


@login_required
def delete_inventory(request, pk):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventory = get_object_or_404(Inventory, id=pk)
    
    if inventory.raw_materials.exists():
        messages.error(request, f'Cannot delete "{inventory.name}" - has {inventory.raw_materials.count()} materials')
        return redirect('inventory:inventory_list')
    
    inventory.delete()
    messages.success(request, 'Inventory deleted')
    return redirect('inventory:inventory_list')


# ==================== Category Management ====================

@login_required
def category_list(request):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    categories = RawMaterialCategory.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def create_category(request):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = RawMaterialCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created')
            return redirect('inventory:category_list')
    else:
        form = RawMaterialCategoryForm()
    
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
def edit_category(request, pk):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    category = get_object_or_404(RawMaterialCategory, id=pk)
    
    if request.method == 'POST':
        form = RawMaterialCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated')
            return redirect('inventory:category_list')
    else:
        form = RawMaterialCategoryForm(instance=category)
    
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
def delete_category(request, pk):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    category = get_object_or_404(RawMaterialCategory, id=pk)
    
    if category.materials.exists():
        messages.error(request, f'Cannot delete "{category.name}" - has {category.materials.count()} materials')
        return redirect('inventory:category_list')
    
    category.delete()
    messages.success(request, 'Category deleted')
    return redirect('inventory:category_list')


@login_required
def create_category_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if not has_inventory_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '')
    
    if not name:
        return JsonResponse({'error': 'Category name required'}, status=400)
    
    if RawMaterialCategory.objects.filter(name__iexact=name).exists():
        return JsonResponse({'error': 'Category already exists'}, status=400)
    
    category = RawMaterialCategory.objects.create(name=name, description=description)
    
    return JsonResponse({'success': True, 'id': str(category.id), 'name': category.name})


# ==================== Raw Material Management ====================

@login_required
def raw_material_list(request):
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.all()
        can_delete = True
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
        can_delete = False
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    categories = RawMaterialCategory.objects.all()
    
    return render(request, 'inventory/raw_material_list.html', {
        'materials': materials,
        'categories': categories,
        'can_delete': can_delete,
    })


@login_required
def create_raw_material(request):
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventories = Inventory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            material = RawMaterial()
            material.name = request.POST.get('name')
            material.sku = request.POST.get('sku')
            material.unit = request.POST.get('unit')
            material.minimum_stock = Decimal(request.POST.get('minimum_stock', 0))
            material.maximum_stock = Decimal(request.POST.get('maximum_stock', 0))
            material.reorder_level = Decimal(request.POST.get('reorder_level', 0))
            material.unit_cost = Decimal(request.POST.get('unit_cost', 0))
            material.inventory_id = request.POST.get('inventory')
            material.current_stock = Decimal(request.POST.get('current_stock', 0))  # Allow initial stock
            material.is_active = request.POST.get('is_active') == 'on'
            material.save()
            
            # If initial stock > 0, create a transaction record
            if material.current_stock > 0:
                StockTransaction.objects.create(
                    raw_material=material,
                    transaction_type='purchase',
                    quantity=material.current_stock,
                    total_cost=material.current_stock * material.unit_cost,
                    unit_cost=material.unit_cost,
                    reference_number=f"INITIAL-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    notes="Initial stock entry",
                    created_by=request.user
                )
            
            messages.success(request, f'Raw material "{material.name}" created')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'inventory/raw_material_form.html', {
        'inventories': inventories,
    })


@login_required
def edit_raw_material(request, pk):
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:raw_material_list')
    
    inventories = Inventory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            material.name = request.POST.get('name')
            material.sku = request.POST.get('sku')
            material.unit = request.POST.get('unit')
            material.minimum_stock = Decimal(request.POST.get('minimum_stock', 0))
            material.maximum_stock = Decimal(request.POST.get('maximum_stock', 0))
            material.reorder_level = Decimal(request.POST.get('reorder_level', 0))
            material.unit_cost = Decimal(request.POST.get('unit_cost', 0))
            material.inventory_id = request.POST.get('inventory')
            material.is_active = request.POST.get('is_active') == 'on'
            # Note: current_stock is not edited here - it's managed through transactions
            material.save()
            
            messages.success(request, f'Raw material "{material.name}" updated')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'inventory/raw_material_form.html', {
        'material': material,
        'inventories': inventories,
    })


@login_required
def delete_raw_material(request, pk):
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if material.recipes.exists():
        messages.error(request, f'Cannot delete "{material.name}" - used in recipes')
        return redirect('inventory:raw_material_list')
    
    material.delete()
    messages.success(request, 'Raw material deleted')
    return redirect('inventory:raw_material_list')


# ==================== Stock Management ====================

@login_required
def current_stock(request):
    """Current Stock - Show all items with period purchase summary"""
    
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.filter(is_active=True)
        can_delete = True
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory, is_active=True)
        can_delete = False
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Get filter parameters
    date_range = request.GET.get('date_range', 'month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    search_query = request.GET.get('search', '')
    
    today = timezone.now().date()
    
    # Calculate date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_range = 'custom'
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
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
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Apply search filter
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Prepare item list with period summary
    items_list = []
    total_value = 0
    low_stock_count = 0
    total_period_quantity = 0
    
    for material in materials:
        # Calculate period purchase summary (total quantity and cost for this item)
        period_purchases = StockTransaction.objects.filter(
            raw_material=material,
            transaction_type='purchase',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(
            total_qty=Sum('quantity'),
            total_cost=Sum('total_cost')
        )
        
        period_qty = period_purchases['total_qty'] or 0
        period_cost = period_purchases['total_cost'] or 0
        
        # Calculate total value
        material_total_value = material.current_stock * material.unit_cost
        total_value += material_total_value
        total_period_quantity += period_qty
        
        if material.current_stock <= material.minimum_stock:
            low_stock_count += 1
        
        items_list.append({
            'id': material.id,
            'name': material.name,
            'sku': material.sku,
            'unit': material.unit,
            'current_stock': material.current_stock,
            'unit_cost': material.unit_cost,
            'minimum_stock': material.minimum_stock,
            'total_value': material_total_value,
            'period_quantity': period_qty,
            'period_cost': period_cost,
        })
    
    # Pagination
    paginator = Paginator(items_list, 20)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    
    context = {
        'items': items_page,
        'total_items': materials.count(),
        'total_value': total_value,
        'total_period_quantity': total_period_quantity,
        'low_stock_count': low_stock_count,
        'date_range': date_range,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
        'search_query': search_query,
        'can_delete': can_delete,
    }
    
    return render(request, 'inventory/current_stock.html', context)


@login_required
def stock_detail(request, pk):
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    transactions = material.transactions.all().order_by('-created_at')
    
    # Calculate total value
    total_value = material.current_stock * material.unit_cost
    
    return render(request, 'inventory/stock_detail.html', {
        'material': material,
        'transactions': transactions,
        'total_value': total_value,  # This is the key
    })


@login_required
def add_stock(request, pk):
    """Add stock to a raw material - Handles GET (form page) and POST (submission)"""
    
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    # Handle GET request - Show the HTML form
    if request.method == 'GET':
        # Calculate current total value for display
        current_value = material.current_stock * material.unit_cost
        return render(request, 'inventory/add_stock_form.html', {
            'material': material,
            'current_value': current_value
        })
    
    # Handle POST request - Process the form submission
    if request.method == 'POST':
        try:
            quantity = Decimal(request.POST.get('quantity', 0))
            total_cost = Decimal(request.POST.get('total_cost', 0))
            reference = request.POST.get('reference_number', '')
            notes = request.POST.get('notes', '')
            
            if quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0')
                return redirect('inventory:add_stock', pk=material.id)
            
            if total_cost <= 0:
                messages.error(request, 'Total cost must be greater than 0')
                return redirect('inventory:add_stock', pk=material.id)
            
            unit_cost = total_cost / quantity
            
            old_stock = material.current_stock
            old_total_value = material.current_stock * material.unit_cost
            
            new_total_value = old_total_value + total_cost
            new_total_quantity = old_stock + quantity
            new_avg_unit_cost = new_total_value / new_total_quantity if new_total_quantity > 0 else unit_cost
            
            material.current_stock = new_total_quantity
            material.unit_cost = new_avg_unit_cost
            material.save()
            
            StockTransaction.objects.create(
                raw_material=material,
                transaction_type='purchase',
                quantity=quantity,
                total_cost=total_cost,
                unit_cost=unit_cost,
                reference_number=reference or f"MANUAL-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                notes=notes or f"Stock added. Old stock: {old_stock}, New stock: {new_total_quantity}",
                created_by=request.user
            )
            
            messages.success(request, f'Successfully added {quantity} {material.unit} of {material.name}')
            return redirect('inventory:purchase_summary', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error adding stock: {str(e)}')
            return redirect('inventory:add_stock', pk=material.id)
    
    return redirect('inventory:purchase_summary')


@login_required
def update_stock(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if not has_inventory_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    new_quantity = Decimal(request.POST.get('new_quantity', 0))
    new_unit_cost = Decimal(request.POST.get('new_unit_cost', 0))
    reason = request.POST.get('reason', '')
    
    if new_quantity < 0:
        return JsonResponse({'error': 'Quantity cannot be negative'}, status=400)
    
    old_quantity = material.current_stock
    old_unit_cost = material.unit_cost
    
    if new_quantity != old_quantity or new_unit_cost != old_unit_cost:
        StockTransaction.objects.create(
            raw_material=material,
            transaction_type='adjustment',
            quantity=abs(new_quantity - old_quantity) if new_quantity != old_quantity else 1,
            unit_cost=new_unit_cost,
            reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Stock adjustment. Reason: {reason}",
            created_by=request.user
        )
    
    material.current_stock = new_quantity
    material.unit_cost = new_unit_cost
    material.save()
    
    return JsonResponse({'success': True, 'message': 'Stock updated successfully'})


# ==================== Stock Requests ====================

@login_required
def stock_requests_list(request):
    if request.user.role == 'admin' or request.user.is_superuser:
        stock_requests = StockRequest.objects.all()
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        stock_requests = StockRequest.objects.filter(inventory=request.user.inventory)
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    stock_requests = stock_requests.order_by('-requested_at')
    
    return render(request, 'inventory/stock_requests.html', {'stock_requests': stock_requests})


@login_required
def create_stock_request_ajax(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['staff', 'manager', 'admin'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    if not request.user.restaurant:
        return JsonResponse({'error': 'No restaurant assigned'}, status=400)
    
    menu_item_id = request.POST.get('menu_item_id')
    quantity = int(request.POST.get('quantity', 0))
    notes = request.POST.get('notes', '')
    
    if not menu_item_id or quantity <= 0:
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    inventory = Inventory.objects.filter(is_active=True).first()
    
    if not inventory:
        return JsonResponse({'error': 'No inventory available'}, status=400)
    
    StockRequest.objects.create(
        restaurant=request.user.restaurant,
        inventory=inventory,
        menu_item=menu_item,
        quantity_requested=quantity,
        status='pending',
        notes=notes
    )
    
    return JsonResponse({'success': True, 'message': f'Stock request for {quantity} x {menu_item.name} sent'})


@login_required
def process_stock_request(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    stock_request = get_object_or_404(StockRequest, id=pk)
    action = request.POST.get('action')
    
    if action == 'approve':
        stock_request.status = 'approved'
        message = 'Request approved'
    elif action == 'reject':
        stock_request.status = 'rejected'
        message = 'Request rejected'
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)
    
    stock_request.save()
    return JsonResponse({'success': True, 'message': message})


@login_required
def fulfill_stock_request(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    stock_request = get_object_or_404(StockRequest, id=pk)
    
    if stock_request.status != 'approved':
        return JsonResponse({'error': 'Request must be approved first'}, status=400)
    
    menu_item = stock_request.menu_item
    
    if menu_item.has_recipe:
        recipes = Recipe.objects.filter(menu_item=menu_item)
        
        for recipe in recipes:
            required = recipe.quantity_required * stock_request.quantity_requested
            if recipe.raw_material.current_stock < required:
                return JsonResponse({'error': f'Insufficient stock for {recipe.raw_material.name}'}, status=400)
        
        for recipe in recipes:
            required = recipe.quantity_required * stock_request.quantity_requested
            recipe.raw_material.current_stock -= required
            recipe.raw_material.save()
            
            StockTransaction.objects.create(
                raw_material=recipe.raw_material,
                transaction_type='transfer',
                quantity=required,
                unit_cost=recipe.raw_material.unit_cost,
                reference_number=f"REQUEST-{stock_request.id}",
                notes=f"Transfer to {stock_request.restaurant.name} for {menu_item.name}",
                created_by=request.user
            )
    else:
        menu_item.quantity += stock_request.quantity_requested
        menu_item.save()
    
    stock_request.status = 'fulfilled'
    stock_request.fulfilled_at = timezone.now()
    stock_request.save()
    
    return JsonResponse({'success': True, 'message': 'Stock request fulfilled'})


# ==================== Dashboard ====================

@login_required
def inventory_dashboard(request):
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.all()
        total_materials = materials.count()
        low_stock_count = materials.filter(current_stock__lte=F('minimum_stock')).count()
        pending_requests = StockRequest.objects.filter(status='pending').count()
        
        total_value = sum(m.current_stock * m.unit_cost for m in materials)
        recent_transactions = StockTransaction.objects.all().order_by('-created_at')[:10]
        
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
        total_materials = materials.count()
        low_stock_count = materials.filter(current_stock__lte=F('minimum_stock')).count()
        pending_requests = StockRequest.objects.filter(inventory=request.user.inventory, status='pending').count()
        
        total_value = sum(m.current_stock * m.unit_cost for m in materials)
        recent_transactions = StockTransaction.objects.filter(
            raw_material__inventory=request.user.inventory
        ).order_by('-created_at')[:10]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    return render(request, 'inventory/dashboard.html', {
        'total_materials': total_materials,
        'low_stock_count': low_stock_count,
        'pending_requests': pending_requests,
        'total_value': total_value,
        'recent_transactions': recent_transactions,
    })


# ==================== Daily Stock Request (New Workflow) ====================

@login_required
def daily_request_create(request):
    """Staff creates daily stock request"""
    if request.user.role != 'staff':
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    today = date.today()
    restaurant = request.user.restaurant
    
    daily_request, created = DailyStockRequest.objects.get_or_create(
        restaurant=restaurant,
        request_date=today,
        defaults={'created_by': request.user}
    )
    
    if request.method == 'POST':
        daily_request.notes = request.POST.get('notes', '')
        daily_request.items.all().delete()
        
        items = request.POST.getlist('items[]')
        quantities = request.POST.getlist('quantities[]')
        
        for item_id, qty in zip(items, quantities):
            if item_id and qty and float(qty) > 0:
                menu_item = get_object_or_404(MenuItem, id=item_id)
                DailyRequestItem.objects.create(
                    daily_request=daily_request,
                    menu_item=menu_item,
                    requested_quantity=Decimal(qty)
                )
        
        daily_request.save()
        messages.success(request, f'Daily stock request submitted for {today}')
        return redirect('inventory:daily_request_list')
    
    menu_items = MenuItem.objects.filter(is_available=True)
    existing_items = daily_request.items.all()
    
    return render(request, 'inventory/daily_request_form.html', {
        'daily_request': daily_request,
        'menu_items': menu_items,
        'existing_items': existing_items,
        'today': today
    })


@login_required
def daily_request_list(request):
    """Staff views all their daily requests"""
    if request.user.role != 'staff':
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    requests = DailyStockRequest.objects.filter(
        restaurant=request.user.restaurant
    ).order_by('-request_date')
    
    return render(request, 'inventory/daily_request_list.html', {'requests': requests})


@login_required
def daily_request_detail(request, pk):
    """View single request details"""
    daily_request = get_object_or_404(DailyStockRequest, id=pk)
    
    if request.user.role == 'staff' and daily_request.restaurant != request.user.restaurant:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    return render(request, 'inventory/daily_request_detail.html', {'daily_request': daily_request})


@login_required
def all_requests_list(request):
    """Admin/Store views all daily requests with advanced filters"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Get filter parameters
    date_range = request.GET.get('date_range', 'today')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status_filter = request.GET.get('status', '')
    restaurant_id = request.GET.get('restaurant', '')
    
    today = timezone.now().date()
    
    # Calculate date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_range = 'custom'
        except (ValueError, TypeError):
            start_date = today
            end_date = today
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
    else:
        start_date = today
        end_date = today
    
    # Base queryset
    requests = DailyStockRequest.objects.filter(
        request_date__gte=start_date,
        request_date__lte=end_date
    ).order_by('-request_date')
    
    # Apply status filter
    if status_filter:
        requests = requests.filter(status=status_filter)
    
    # Apply restaurant filter
    selected_restaurant_name = None
    if restaurant_id:
        requests = requests.filter(restaurant_id=restaurant_id)
        try:
            selected_restaurant_name = Restaurant.objects.get(id=restaurant_id).name
        except:
            pass
    
    # Pagination
    paginator = Paginator(requests, 20)
    page = request.GET.get('page')
    requests_page = paginator.get_page(page)
    
    # Calculate statistics
    total_requests = requests.count()
    pending_count = requests.filter(status='pending').count()
    completed_count = requests.filter(status='completed').count()
    total_items = sum(req.items.count() for req in requests)
    
    # Get all restaurants for filter dropdown
    restaurants = Restaurant.objects.filter(is_active=True)
    
    context = {
        'requests': requests_page,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'total_items': total_items,
        'restaurants': restaurants,
        'date_range': date_range,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'status_filter': status_filter,
        'selected_restaurant': restaurant_id,
        'selected_restaurant_name': selected_restaurant_name,
    }
    
    return render(request, 'inventory/all_requests_list.html', context)


login_required
def consolidated_summary(request):
    """Admin AND Store can see consolidated summary with batch generation"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    selected_date = request.GET.get('date', date.today())
    
    # Get all pending requests for the selected date
    requests = DailyStockRequest.objects.filter(
        request_date=selected_date,
        status__in=['pending', 'processing']
    ).prefetch_related('items__menu_item')
    
    consolidated = {}
    for req in requests:
        for item in req.items.all():
            key = item.menu_item.id
            if key not in consolidated:
                consolidated[key] = {
                    'menu_item': item.menu_item,
                    'total_requested': 0,
                    'restaurants': []
                }
            consolidated[key]['total_requested'] += item.requested_quantity
            consolidated[key]['restaurants'].append({
                'name': req.restaurant.name,
                'request_id': req.id,
                'quantity': item.requested_quantity
            })
    
    # Check if production batches already exist for these items
    existing_batches = ProductionBatch.objects.filter(
        menu_item__in=[item['menu_item'].id for item in consolidated.values()],
        produced_at__date=selected_date
    )
    existing_batch_ids = [batch.menu_item_id for batch in existing_batches]
    
    return render(request, 'inventory/consolidated_summary.html', {
        'consolidated': consolidated.values(),
        'selected_date': selected_date,
        'existing_batch_ids': existing_batch_ids
    })

@login_required
def add_production_batch(request):
    """Admin/Store adds production batch"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        menu_item_id = request.POST.get('menu_item')
        batch_number = request.POST.get('batch_number', '')
        quantity = Decimal(request.POST.get('quantity', 0))
        notes = request.POST.get('notes', '')
        
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        
        # If batch number is empty, generate one
        if not batch_number:
            from datetime import datetime
            item_code = menu_item.name[:3].upper().replace(' ', '')
            batch_number = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{item_code}"
        
        # Check if batch number already exists
        if ProductionBatch.objects.filter(batch_number=batch_number).exists():
            messages.error(request, f'Batch number "{batch_number}" already exists!')
            return redirect('inventory:add_production_batch')
        
        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than 0')
            return redirect('inventory:add_production_batch')
        
        # Create production batch
        batch = ProductionBatch.objects.create(
            menu_item=menu_item,
            batch_number=batch_number,
            quantity_produced=quantity,
            notes=notes,
            produced_by=request.user
        )
        
        # Update menu item stock
        menu_item.quantity += quantity
        menu_item.save()
        
        messages.success(request, f'Production batch "{batch_number}" created for {menu_item.name}. Added {quantity} to stock.')
        return redirect('inventory:production_batches')
    
    menu_items = MenuItem.objects.filter(is_available=True)
    return render(request, 'inventory/add_production_batch.html', {'menu_items': menu_items})

@login_required
def production_batches(request):
    """List all production batches"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    batches = ProductionBatch.objects.all().order_by('-produced_at')
    return render(request, 'inventory/production_batches.html', {'batches': batches})


@login_required
def dispatch_to_restaurant(request, request_id):
    """Dispatch produced items to restaurant"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    daily_request = get_object_or_404(DailyStockRequest, id=request_id)
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('qty_'):
                item_id = key.split('_')[1]
                dispatch_qty = Decimal(value)
                if dispatch_qty > 0:
                    menu_item = get_object_or_404(MenuItem, id=item_id)
                    
                    DispatchRecord.objects.create(
                        daily_request=daily_request,
                        menu_item=menu_item,
                        quantity=dispatch_qty,
                        dispatched_by=request.user
                    )
                    
                    req_item = daily_request.items.filter(menu_item=menu_item).first()
                    if req_item:
                        req_item.fulfilled_quantity += dispatch_qty
                        req_item.save()
                    
                    menu_item.quantity += dispatch_qty
                    menu_item.save()
        
        # Update request status
        all_fulfilled = all(
            item.fulfilled_quantity >= item.requested_quantity 
            for item in daily_request.items.all()
        )
        daily_request.status = 'completed' if all_fulfilled else 'processing'
        daily_request.save()
        
        messages.success(request, f'Dispatch completed for {daily_request.restaurant.name}')
        return redirect('inventory:all_requests_list')
    
    return render(request, 'inventory/dispatch_form.html', {'daily_request': daily_request})


@login_required
def generate_production_batch(request):
    """Generate production batch from consolidated summary"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        menu_item_id = request.POST.get('menu_item_id')
        batch_number = request.POST.get('batch_number')
        quantity_produced = Decimal(request.POST.get('quantity_produced', 0))
        notes = request.POST.get('notes', '')
        
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        
        # Check if batch number already exists
        if ProductionBatch.objects.filter(batch_number=batch_number).exists():
            messages.error(request, f'Batch number "{batch_number}" already exists. Please use a different number.')
            return redirect('inventory:consolidated_summary')
        
        # Create production batch
        batch = ProductionBatch.objects.create(
            menu_item=menu_item,
            batch_number=batch_number,
            quantity_produced=quantity_produced,
            notes=notes,
            produced_by=request.user
        )
        
        messages.success(request, f'Production batch "{batch_number}" created for {menu_item.name}')
        return redirect('inventory:production_batches')
    
    return redirect('inventory:consolidated_summary')


@login_required
def edit_transaction(request, pk):
    """Edit a stock transaction"""
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    transaction = get_object_or_404(StockTransaction, id=pk)
    material = transaction.raw_material
    
    # Check permission
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    # Only allow editing purchase transactions
    if transaction.transaction_type != 'purchase':
        messages.error(request, 'Only purchase transactions can be edited')
        return redirect('inventory:stock_detail', pk=material.id)
    
    if request.method == 'POST':
        try:
            old_quantity = transaction.quantity
            old_total_cost = transaction.total_cost
            old_unit_cost = transaction.unit_cost
            
            new_quantity = Decimal(request.POST.get('quantity', 0))
            new_total_cost = Decimal(request.POST.get('total_cost', 0))
            new_reference = request.POST.get('reference_number', '')
            new_notes = request.POST.get('notes', '')
            
            if new_quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0')
                return redirect('inventory:edit_transaction', pk=transaction.id)
            
            if new_total_cost <= 0:
                messages.error(request, 'Total cost must be greater than 0')
                return redirect('inventory:edit_transaction', pk=transaction.id)
            
            new_unit_cost = new_total_cost / new_quantity
            
            # Update the transaction
            transaction.quantity = new_quantity
            transaction.total_cost = new_total_cost
            transaction.unit_cost = new_unit_cost
            transaction.reference_number = new_reference
            transaction.notes = new_notes
            transaction.save()
            
            # Recalculate material stock and average cost
            # First, remove the old transaction's effect
            old_total_value = material.current_stock * material.unit_cost
            
            # Remove old transaction contribution
            adjusted_total_value = old_total_value - old_total_cost
            adjusted_total_quantity = material.current_stock - old_quantity
            
            # Add new transaction contribution
            new_total_value = adjusted_total_value + new_total_cost
            new_total_quantity = adjusted_total_quantity + new_quantity
            
            # Update material
            material.current_stock = new_total_quantity
            if new_total_quantity > 0:
                material.unit_cost = new_total_value / new_total_quantity
            else:
                material.unit_cost = 0
            material.save()
            
            messages.success(request, 'Transaction updated successfully')
            return redirect('inventory:stock_detail', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error updating transaction: {str(e)}')
            return redirect('inventory:edit_transaction', pk=transaction.id)
    
    # Calculate current value for display
    current_value = material.current_stock * material.unit_cost
    
    context = {
        'transaction': transaction,
        'material': material,
        'current_value': current_value,
    }
    return render(request, 'inventory/edit_transaction.html', context)


@login_required
def delete_transaction(request, pk):
    """Delete a stock transaction"""
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    transaction = get_object_or_404(StockTransaction, id=pk)
    material = transaction.raw_material
    
    # Check permission
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    # Only allow deleting purchase transactions
    if transaction.transaction_type != 'purchase':
        messages.error(request, 'Only purchase transactions can be deleted')
        return redirect('inventory:stock_detail', pk=material.id)
    
    if request.method == 'POST':
        try:
            # Remove transaction effect from material
            old_total_value = material.current_stock * material.unit_cost
            new_total_value = old_total_value - transaction.total_cost
            new_total_quantity = material.current_stock - transaction.quantity
            
            material.current_stock = new_total_quantity
            if new_total_quantity > 0:
                material.unit_cost = new_total_value / new_total_quantity
            else:
                material.unit_cost = 0
            material.save()
            
            # Delete the transaction
            transaction.delete()
            
            messages.success(request, 'Transaction deleted successfully')
            return redirect('inventory:stock_detail', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error deleting transaction: {str(e)}')
            return redirect('inventory:stock_detail', pk=material.id)
    
    context = {
        'transaction': transaction,
        'material': material,
    }
    return render(request, 'inventory/delete_transaction.html', context)


@login_required
def update_stock(request, pk):
    """Update stock - Set new quantity and/or unit cost (for stock corrections)"""
    
    if not has_inventory_access(request.user):
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    # Handle GET request - Show the form
    if request.method == 'GET':
        current_total_value = material.current_stock * material.unit_cost
        return render(request, 'inventory/update_stock_form.html', {
            'material': material,
            'current_total_value': current_total_value,
        })
    
    # Handle POST request - Process the update
    if request.method == 'POST':
        try:
            new_quantity = Decimal(request.POST.get('new_quantity', 0))
            new_unit_cost = Decimal(request.POST.get('new_unit_cost', 0))
            reason = request.POST.get('reason', '')
            
            if new_quantity < 0:
                messages.error(request, 'Quantity cannot be negative')
                return redirect('inventory:update_stock', pk=material.id)
            
            if new_unit_cost < 0:
                messages.error(request, 'Unit cost cannot be negative')
                return redirect('inventory:update_stock', pk=material.id)
            
            old_quantity = material.current_stock
            old_unit_cost = material.unit_cost
            old_total_value = old_quantity * old_unit_cost
            new_total_value = new_quantity * new_unit_cost
            
            # Calculate adjustment amount
            quantity_difference = new_quantity - old_quantity
            value_difference = new_total_value - old_total_value
            
            # Create transaction record for audit
            StockTransaction.objects.create(
                raw_material=material,
                transaction_type='adjustment',
                quantity=abs(quantity_difference) if quantity_difference != 0 else 1,
                unit_cost=new_unit_cost if new_unit_cost > 0 else old_unit_cost,
                total_cost=abs(value_difference) if value_difference != 0 else 0,
                reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                notes=f"Stock adjustment. Reason: {reason}. Changed from {old_quantity} to {new_quantity}, Unit cost from {old_unit_cost} to {new_unit_cost}",
                created_by=request.user
            )
            
            # Update material
            material.current_stock = new_quantity
            if new_unit_cost > 0:
                material.unit_cost = new_unit_cost
            material.save()
            
            messages.success(request, f'Stock updated successfully! Quantity: {old_quantity} → {new_quantity} {material.unit}')
            return redirect('inventory:stock_detail', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error updating stock: {str(e)}')
            return redirect('inventory:update_stock', pk=material.id)
    
    return redirect('inventory:current_stock')



@login_required
def purchase_summary(request):
    """Purchase Summary - Item-wise total purchase details based on date range"""
    
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.filter(is_active=True)
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory, is_active=True)
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Get filter parameters
    date_range = request.GET.get('date_range', 'month')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    search_query = request.GET.get('search', '')
    
    today = timezone.now().date()
    
    # Calculate date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_range = 'custom'
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
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
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Calculate Today's summary
    today_purchases = StockTransaction.objects.filter(
        transaction_type='purchase',
        created_at__date=today
    )
    today_items = today_purchases.count()
    today_cost = today_purchases.aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Calculate Monthly summary
    start_of_month = today.replace(day=1)
    monthly_purchases = StockTransaction.objects.filter(
        transaction_type='purchase',
        created_at__date__gte=start_of_month,
        created_at__date__lte=today
    )
    monthly_items = monthly_purchases.count()
    monthly_cost = monthly_purchases.aggregate(total=Sum('total_cost'))['total'] or 0
    
    # Apply search filter
    if search_query:
        materials = materials.filter(
            Q(name__icontains=search_query) |
            Q(sku__icontains=search_query)
        )
    
    # Prepare item-wise purchase summary - SHOW ALL ITEMS
    items_list = []
    total_purchase_cost = 0
    total_quantity = 0
    
    for material in materials:
        # Get purchase transactions for this material in date range
        purchases = StockTransaction.objects.filter(
            raw_material=material,
            transaction_type='purchase',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Calculate totals (will be 0 if no purchases)
        total_qty = purchases.aggregate(total=Sum('quantity'))['total'] or 0
        total_cost_val = purchases.aggregate(total=Sum('total_cost'))['total'] or 0
        purchase_count = purchases.count()
        
        # Calculate average unit cost (if there are purchases)
        avg_unit_cost = total_cost_val / total_qty if total_qty > 0 else 0
        
        items_list.append({
            'id': material.id,
            'name': material.name,
            'sku': material.sku,
            'unit': material.unit,
            'total_quantity': total_qty,
            'total_cost': total_cost_val,
            'avg_unit_cost': avg_unit_cost,
            'purchase_count': purchase_count,
        })
        
        total_purchase_cost += total_cost_val
        total_quantity += total_qty
    
    # Sort by name
    items_list.sort(key=lambda x: x['name'])
    
    # Pagination
    paginator = Paginator(items_list, 20)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    
    context = {
        'items': items_page,
        'total_items': materials.count(),
        'total_purchase_cost': total_purchase_cost,
        'total_quantity': total_quantity,
        'today_items': today_items,
        'today_cost': today_cost,
        'monthly_items': monthly_items,
        'monthly_cost': monthly_cost,
        'date_range': date_range,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'search_query': search_query,
    }
    
    return render(request, 'inventory/purchase_summary.html', context)


@login_required
def item_transactions(request, item_id):
    """Get purchase transactions for a specific item (AJAX) - only for selected date range"""
    
    if not has_inventory_access(request.user):
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    material = get_object_or_404(RawMaterial, id=item_id)
    
    # Get date range from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    date_range = request.GET.get('date_range', 'month')
    
    today = timezone.now().date()
    
    # Calculate date range same as purchase_summary
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = today - timedelta(days=30)
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
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
    else:
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Get transactions
    transactions = StockTransaction.objects.filter(
        raw_material=material,
        transaction_type='purchase',
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by('-created_at')
    
    total_quantity = transactions.aggregate(total=Sum('quantity'))['total'] or 0
    total_cost = transactions.aggregate(total=Sum('total_cost'))['total'] or 0
    
    transaction_list = []
    for trans in transactions:
        transaction_list.append({
            'date': trans.created_at.strftime('%Y-%m-%d %H:%M'),
            'quantity': float(trans.quantity),
            'unit_cost': float(trans.unit_cost),
            'total_cost': float(trans.total_cost or (trans.quantity * trans.unit_cost)),
            'reference': trans.reference_number,
            'notes': trans.notes,
        })
    
    return JsonResponse({
        'success': True,
        'transactions': transaction_list,
        'total_quantity': float(total_quantity),
        'total_cost': float(total_cost),
        'purchase_count': transactions.count(),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'unit': material.unit,
    })


# apps/inventory/views.py - Fix these functions

@login_required
def production_dispatch_report(request):
    """Production Dispatch Report - Product vs Restaurant matrix"""
    
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Get filter parameters
    date_range = request.GET.get('date_range', 'today')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    search_query = request.GET.get('search', '')
    
    today = timezone.now().date()
    
    # Calculate date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            date_range = 'custom'
        except (ValueError, TypeError):
            start_date = today
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
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
    else:
        start_date = today
        end_date = today
    
    # Get all active restaurants
    restaurants = Restaurant.objects.filter(is_active=True)
    
    # Get all menu items (products)
    products = MenuItem.objects.filter(is_available=True)
    if search_query:
        products = products.filter(name__icontains=search_query)
    products = products.order_by('name')
    
    # Get dispatch records for date range - FIXED: Use dispatched_at instead of created_at
    dispatches = DispatchRecord.objects.filter(
        dispatched_at__date__gte=start_date,
        dispatched_at__date__lte=end_date
    ).select_related('daily_request__restaurant', 'menu_item')
    
    # Get production batches for date range - FIXED: Use produced_at
    productions = ProductionBatch.objects.filter(
        produced_at__date__gte=start_date,
        produced_at__date__lte=end_date
    )
    
    # Calculate totals
    total_production = productions.aggregate(total=Sum('quantity_produced'))['total'] or 0
    total_dispatched = dispatches.aggregate(total=Sum('quantity'))['total'] or 0
    total_pending = total_production - total_dispatched
    
    # Prepare product data
    products_data = []
    restaurant_totals = {r.id: 0 for r in restaurants}
    
    for product in products:
        # Dispatch data per restaurant
        dispatch_data = {}
        product_total = 0
        
        for restaurant in restaurants:
            qty = dispatches.filter(
                menu_item=product,
                daily_request__restaurant=restaurant
            ).aggregate(total=Sum('quantity'))['total'] or 0
            dispatch_data[restaurant.id] = qty
            product_total += qty
            restaurant_totals[restaurant.id] += qty
        
        # Production for this product
        product_production = productions.filter(
            menu_item=product
        ).aggregate(total=Sum('quantity_produced'))['total'] or 0
        
        products_data.append({
            'id': product.id,
            'name': product.name,
            'sku': getattr(product, 'sku', ''),
            'unit': getattr(product, 'unit', 'pcs'),
            'dispatch_data': dispatch_data,
            'total_dispatched': product_total,
            'total_production': product_production,
            'pending': product_production - product_total,
        })
    
    context = {
        'products': products_data,
        'restaurants': restaurants,
        'restaurant_totals': restaurant_totals,
        'total_production': total_production,
        'total_dispatched': total_dispatched,
        'total_pending': total_pending,
        'date_range': date_range,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'search_query': search_query,
    }
    
    return render(request, 'inventory/production_dispatch_report.html', context)


@login_required
def dispatch_details(request, product_id, restaurant_id):
    """Get dispatch details for a specific product and restaurant (AJAX)"""
    
    if request.user.role not in ['admin', 'superadmin', 'store']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Get date range from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    date_range = request.GET.get('date_range', 'today')
    
    today = timezone.now().date()
    
    # Calculate date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = today
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = today
        end_date = today
    
    product = get_object_or_404(MenuItem, id=product_id)
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # FIXED: Use dispatched_at instead of created_at
    dispatches = DispatchRecord.objects.filter(
        menu_item=product,
        daily_request__restaurant=restaurant,
        dispatched_at__date__gte=start_date,
        dispatched_at__date__lte=end_date
    ).order_by('-dispatched_at')
    
    total_quantity = dispatches.aggregate(total=Sum('quantity'))['total'] or 0
    
    dispatch_list = []
    for dispatch in dispatches:
        dispatch_list.append({
            'date': dispatch.dispatched_at.strftime('%Y-%m-%d %H:%M'),
            'quantity': float(dispatch.quantity),
            'request_id': str(dispatch.daily_request.id) if dispatch.daily_request else None,
            'dispatched_by': dispatch.dispatched_by.get_full_name() if dispatch.dispatched_by else None,
        })
    
    return JsonResponse({
        'success': True,
        'dispatches': dispatch_list,
        'total_quantity': float(total_quantity),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    })


@login_required
def product_dispatch_details(request, product_id):
    """Get all dispatch details for a specific product (AJAX)"""
    
    if request.user.role not in ['admin', 'superadmin', 'store']:
        return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
    
    # Get date range from request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    date_range = request.GET.get('date_range', 'today')
    
    today = timezone.now().date()
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            start_date = today
            end_date = today
    elif date_range == 'today':
        start_date = today
        end_date = today
    elif date_range == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif date_range == 'month':
        start_date = today.replace(day=1)
        end_date = today
    else:
        start_date = today
        end_date = today
    
    product = get_object_or_404(MenuItem, id=product_id)
    
    # FIXED: Use dispatched_at instead of created_at
    dispatches = DispatchRecord.objects.filter(
        menu_item=product,
        dispatched_at__date__gte=start_date,
        dispatched_at__date__lte=end_date
    ).order_by('-dispatched_at').select_related('daily_request__restaurant')
    
    total_quantity = dispatches.aggregate(total=Sum('quantity'))['total'] or 0
    
    dispatch_list = []
    for dispatch in dispatches:
        dispatch_list.append({
            'date': dispatch.dispatched_at.strftime('%Y-%m-%d %H:%M'),
            'restaurant': dispatch.daily_request.restaurant.name if dispatch.daily_request else '-',
            'quantity': float(dispatch.quantity),
            'request_id': str(dispatch.daily_request.id) if dispatch.daily_request else None,
        })
    
    return JsonResponse({
        'success': True,
        'dispatches': dispatch_list,
        'total_quantity': float(total_quantity),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
    })