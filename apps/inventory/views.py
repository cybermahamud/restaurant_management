# apps/inventory/views.py
from datetime import date
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
from apps.restaurant.models import MenuItem, Recipe


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
    
    categories = RawMaterialCategory.objects.all()
    inventories = Inventory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            material = RawMaterial()
            material.name = request.POST.get('name')
            material.sku = request.POST.get('sku')
            material.category_id = request.POST.get('category') or None
            material.unit = request.POST.get('unit')
            material.minimum_stock = Decimal(request.POST.get('minimum_stock', 0))
            material.maximum_stock = Decimal(request.POST.get('maximum_stock', 0))
            material.reorder_level = Decimal(request.POST.get('reorder_level', 0))
            material.unit_cost = Decimal(request.POST.get('unit_cost', 0))
            material.inventory_id = request.POST.get('inventory')
            material.is_active = request.POST.get('is_active') == 'on'
            material.save()
            
            messages.success(request, f'Raw material "{material.name}" created')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'inventory/raw_material_form.html', {
        'categories': categories,
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
    
    categories = RawMaterialCategory.objects.all()
    inventories = Inventory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            material.name = request.POST.get('name')
            material.sku = request.POST.get('sku')
            material.category_id = request.POST.get('category') or None
            material.unit = request.POST.get('unit')
            material.minimum_stock = Decimal(request.POST.get('minimum_stock', 0))
            material.maximum_stock = Decimal(request.POST.get('maximum_stock', 0))
            material.reorder_level = Decimal(request.POST.get('reorder_level', 0))
            material.unit_cost = Decimal(request.POST.get('unit_cost', 0))
            material.inventory_id = request.POST.get('inventory')
            material.is_active = request.POST.get('is_active') == 'on'
            material.save()
            
            messages.success(request, f'Raw material "{material.name}" updated')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'inventory/raw_material_form.html', {
        'material': material,
        'categories': categories,
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
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.all()
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    categories = RawMaterialCategory.objects.all()
    pending_requests = StockRequest.objects.filter(status='pending').count()
    
    return render(request, 'inventory/current_stock.html', {
        'materials': materials,
        'categories': categories,
        'pending_requests': pending_requests,
    })


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


# @login_required
# def add_stock(request, pk):
#     if request.method != 'POST':
#         return JsonResponse({'error': 'Invalid method'}, status=400)
    
#     if not has_inventory_access(request.user):
#         return JsonResponse({'error': 'Access denied'}, status=403)
    
#     material = get_object_or_404(RawMaterial, id=pk)
    
#     if request.user.role == 'store' and material.inventory != request.user.inventory:
#         return JsonResponse({'error': 'Access denied'}, status=403)
    
#     quantity = Decimal(request.POST.get('quantity', 0))
#     total_cost = Decimal(request.POST.get('total_cost', 0))
#     reference = request.POST.get('reference_number', '')
#     notes = request.POST.get('notes', '')
    
#     if quantity <= 0:
#         return JsonResponse({'error': 'Quantity must be greater than 0'}, status=400)
    
#     if total_cost <= 0:
#         return JsonResponse({'error': 'Total cost must be greater than 0'}, status=400)
    
#     unit_cost = total_cost / quantity
    
#     old_stock = material.current_stock
#     old_total_value = material.current_stock * material.unit_cost
    
#     new_total_value = old_total_value + total_cost
#     new_total_quantity = old_stock + quantity
#     new_avg_unit_cost = new_total_value / new_total_quantity if new_total_quantity > 0 else unit_cost
    
#     material.current_stock = new_total_quantity
#     material.unit_cost = new_avg_unit_cost
#     material.save()
    
#     StockTransaction.objects.create(
#         raw_material=material,
#         transaction_type='purchase',
#         quantity=quantity,
#         total_cost=total_cost,
#         unit_cost=unit_cost,
#         reference_number=reference,
#         notes=notes,
#         created_by=request.user
#     )
    
#     return JsonResponse({
#         'success': True,
#         'message': f'Added {quantity} {material.unit} of {material.name}',
#         'new_stock': float(new_total_quantity),
#         'new_unit_cost': float(new_avg_unit_cost),
#     })

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
            return redirect('inventory:stock_detail', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error adding stock: {str(e)}')
            return redirect('inventory:add_stock', pk=material.id)
    
    return redirect('inventory:current_stock')


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
    """Admin/Store views all daily requests"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    date_filter = request.GET.get('date')
    if date_filter:
        requests = DailyStockRequest.objects.filter(request_date=date_filter).order_by('-request_date')
    else:
        requests = DailyStockRequest.objects.all().order_by('-request_date')
    
    return render(request, 'inventory/all_requests_list.html', {
        'requests': requests,
        'selected_date': date_filter
    })


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
        quantity = Decimal(request.POST.get('quantity', 0))
        batch_number = request.POST.get('batch_number', '')
        notes = request.POST.get('notes', '')
        
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        
        ProductionBatch.objects.create(
            menu_item=menu_item,
            batch_number=batch_number,
            quantity_produced=quantity,
            produced_by=request.user,
            notes=notes
        )
        
        messages.success(request, f'Batch {batch_number} added for {menu_item.name}')
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