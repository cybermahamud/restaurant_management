# apps/inventory/views.py
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q, F
from django.http import JsonResponse
from django.utils import timezone
from decimal import Decimal
import json

from .models import RawMaterial, RawMaterialCategory, Inventory, StockTransaction, StockRequest, WastageRecord
from .forms import RawMaterialForm, RawMaterialCategoryForm, InventoryForm, AddStockForm, UpdateStockForm
from apps.restaurant.models import MenuItem, Recipe

# ==================== Inventory Management ====================

@login_required
def inventory_list(request):
    """List all inventories"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventories = Inventory.objects.all()
    return render(request, 'inventory/inventory_list.html', {'inventories': inventories})


@login_required
def create_inventory(request):
    """Create new inventory"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = InventoryForm(request.POST)
        if form.is_valid():
            inventory = form.save()
            messages.success(request, f'Inventory "{inventory.name}" created successfully')
            return redirect('inventory:inventory_list')
    else:
        form = InventoryForm()
    
    return render(request, 'inventory/inventory_form.html', {'form': form, 'title': 'Create Inventory'})


@login_required
def edit_inventory(request, pk):
    """Edit inventory"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventory = get_object_or_404(Inventory, id=pk)
    
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory updated successfully')
            return redirect('inventory:inventory_list')
    else:
        form = InventoryForm(instance=inventory)
    
    return render(request, 'inventory/inventory_form.html', {'form': form, 'title': 'Edit Inventory'})


@login_required
def delete_inventory(request, pk):
    """Delete inventory"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    inventory = get_object_or_404(Inventory, id=pk)
    
    if inventory.raw_materials.exists():
        messages.error(request, f'Cannot delete "{inventory.name}" because it has {inventory.raw_materials.count()} raw materials.')
        return redirect('inventory:inventory_list')
    
    inventory.delete()
    messages.success(request, 'Inventory deleted successfully')
    return redirect('inventory:inventory_list')


# ==================== Category Management ====================

@login_required
def category_list(request):
    """List all categories"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    categories = RawMaterialCategory.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def create_category(request):
    """Create category"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = RawMaterialCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully')
            return redirect('inventory:category_list')
    else:
        form = RawMaterialCategoryForm()
    
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Create Category'})


@login_required
def edit_category(request, pk):
    """Edit category"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    category = get_object_or_404(RawMaterialCategory, id=pk)
    
    if request.method == 'POST':
        form = RawMaterialCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully')
            return redirect('inventory:category_list')
    else:
        form = RawMaterialCategoryForm(instance=category)
    
    return render(request, 'inventory/category_form.html', {'form': form, 'title': 'Edit Category'})


@login_required
def delete_category(request, pk):
    """Delete category"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    category = get_object_or_404(RawMaterialCategory, id=pk)
    
    if category.materials.exists():
        messages.error(request, f'Cannot delete "{category.name}" because it has {category.materials.count()} materials.')
        return redirect('inventory:category_list')
    
    category.delete()
    messages.success(request, 'Category deleted successfully')
    return redirect('inventory:category_list')


@login_required
def create_category_ajax(request):
    """Create category via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '')
    
    if not name:
        return JsonResponse({'error': 'Category name is required'}, status=400)
    
    if RawMaterialCategory.objects.filter(name__iexact=name).exists():
        return JsonResponse({'error': 'Category already exists'}, status=400)
    
    category = RawMaterialCategory.objects.create(name=name, description=description)
    
    return JsonResponse({'success': True, 'id': str(category.id), 'name': category.name})


# ==================== Raw Material Management ====================

@login_required
def raw_material_list(request):
    """List all raw materials"""
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
    
    context = {
        'materials': materials,
        'categories': categories,
        'can_delete': can_delete,
    }
    return render(request, 'inventory/raw_material_list.html', context)


@login_required
def create_raw_material(request):
    """Create new raw material"""
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
            
            messages.success(request, f'Raw material "{material.name}" created successfully')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'categories': categories,
        'inventories': inventories,
    }
    return render(request, 'inventory/raw_material_form.html', context)


@login_required
def edit_raw_material(request, pk):
    """Edit raw material"""
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
            
            messages.success(request, f'Raw material "{material.name}" updated successfully')
            return redirect('inventory:raw_material_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    context = {
        'material': material,
        'categories': categories,
        'inventories': inventories,
    }
    return render(request, 'inventory/raw_material_form.html', context)


@login_required
def delete_raw_material(request, pk):
    """Delete raw material"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if material.recipes.exists():
        messages.error(request, f'Cannot delete "{material.name}" because it is used in recipes.')
        return redirect('inventory:raw_material_list')
    
    material.delete()
    messages.success(request, 'Raw material deleted successfully')
    return redirect('inventory:raw_material_list')


# ==================== Stock Management ====================

@login_required
def current_stock(request):
    """View current stock levels"""
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
    
    context = {
        'materials': materials,
        'categories': categories,
        'pending_requests': pending_requests,
    }
    return render(request, 'inventory/current_stock.html', context)


@login_required
def stock_detail(request, pk):
    """View stock details and history for a material"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        messages.error(request, 'Access denied')
        return redirect('inventory:current_stock')
    
    transactions = material.transactions.all().order_by('-created_at')
    
    context = {
        'material': material,
        'transactions': transactions,
    }
    return render(request, 'inventory/stock_detail.html', context)


@login_required
def add_stock(request, pk):
    """Add stock to a material - Manager provides quantity and total cost only"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get form data
    quantity = Decimal(request.POST.get('quantity', 0))
    total_cost = Decimal(request.POST.get('total_cost', 0))
    reference = request.POST.get('reference_number', '')
    notes = request.POST.get('notes', '')
    
    # Validate
    if quantity <= 0:
        return JsonResponse({'error': 'Quantity must be greater than 0'}, status=400)
    
    if total_cost <= 0:
        return JsonResponse({'error': 'Total cost must be greater than 0'}, status=400)
    
    # Calculate unit cost
    unit_cost = total_cost / quantity
    
    # Get current stock and value for weighted average calculation
    old_stock = material.current_stock
    old_total_value = material.current_stock * material.unit_cost
    
    # Calculate new weighted average unit cost
    new_total_value = old_total_value + total_cost
    new_total_quantity = old_stock + quantity
    new_avg_unit_cost = new_total_value / new_total_quantity if new_total_quantity > 0 else unit_cost
    
    # Update material
    material.current_stock = new_total_quantity
    material.unit_cost = new_avg_unit_cost
    material.save()
    
    # Create transaction record
    StockTransaction.objects.create(
        raw_material=material,
        transaction_type='purchase',
        quantity=quantity,
        total_cost=total_cost,
        unit_cost=unit_cost,  # This will be auto-calculated in save()
        reference_number=reference,
        notes=notes,
        created_by=request.user
    )
    
    return JsonResponse({
        'success': True, 
        'message': f'Added {quantity} {material.unit} of {material.name}',
        'new_stock': float(new_total_quantity),
        'new_unit_cost': float(new_avg_unit_cost),
        'total_cost': float(total_cost)
    })


@login_required
def update_stock(request, pk):
    """Update stock quantity and cost (correction)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.user.role == 'store' and material.inventory != request.user.inventory:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    new_quantity = Decimal(request.POST.get('new_quantity', 0))
    new_unit_cost = Decimal(request.POST.get('new_unit_cost', 0))
    reason = request.POST.get('reason', '')
    
    old_quantity = material.current_stock
    old_unit_cost = material.unit_cost
    
    if new_quantity < 0:
        return JsonResponse({'error': 'Quantity cannot be negative'}, status=400)
    
    # Create adjustment transaction
    if new_quantity != old_quantity or new_unit_cost != old_unit_cost:
        StockTransaction.objects.create(
            raw_material=material,
            transaction_type='adjustment',
            quantity=abs(new_quantity - old_quantity) if new_quantity != old_quantity else 1,
            unit_cost=new_unit_cost,
            reference_number=f"ADJ-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Stock adjustment. Reason: {reason}. Changed from {old_quantity} to {new_quantity}, Cost from {old_unit_cost} to {new_unit_cost}",
            created_by=request.user
        )
    
    # Update stock
    material.current_stock = new_quantity
    material.unit_cost = new_unit_cost
    material.save()
    
    return JsonResponse({'success': True, 'message': 'Stock updated successfully'})


# ==================== Stock Requests ====================

@login_required
def stock_requests_list(request):
    """List all stock requests"""
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
    """Create stock request from restaurant to inventory"""
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
    """Process stock request (approve/reject)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        stock_request = get_object_or_404(StockRequest, id=pk)
        action = request.POST.get('action')
        
        if action == 'approve':
            stock_request.status = 'approved'
            message = 'Request approved successfully'
        elif action == 'reject':
            stock_request.status = 'rejected'
            message = 'Request rejected'
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        stock_request.save()
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def fulfill_stock_request(request, pk):
    """Fulfill a stock request (transfer stock to restaurant)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        stock_request = get_object_or_404(StockRequest, id=pk)
        
        if stock_request.status != 'approved':
            return JsonResponse({'error': 'Request must be approved first'}, status=400)
        
        menu_item = stock_request.menu_item
        
        # Check if menu item has recipe and sufficient stock
        if menu_item.has_recipe:
            recipes = Recipe.objects.filter(menu_item=menu_item)
            
            # Check stock availability
            for recipe in recipes:
                required = recipe.quantity_required * stock_request.quantity_requested
                if recipe.raw_material.current_stock < required:
                    return JsonResponse({
                        'error': f'Insufficient stock for {recipe.raw_material.name}. Required: {required}, Available: {recipe.raw_material.current_stock}'
                    }, status=400)
            
            # Deduct stock
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
            # For items without recipe, just update menu item stock
            menu_item.quantity += stock_request.quantity_requested
            menu_item.save()
        
        stock_request.status = 'fulfilled'
        stock_request.fulfilled_at = timezone.now()
        stock_request.save()
        
        return JsonResponse({'success': True, 'message': 'Stock request fulfilled successfully'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ==================== Dashboard ====================

@login_required
def inventory_dashboard(request):
    """Inventory dashboard"""
    if request.user.role == 'admin' or request.user.is_superuser:
        materials = RawMaterial.objects.all()
        total_materials = materials.count()
        low_stock_count = materials.filter(current_stock__lte=F('minimum_stock')).count()
        pending_requests = StockRequest.objects.filter(status='pending').count()
        
        # Calculate total inventory value
        total_value = 0
        for material in materials:
            total_value += material.current_stock * material.unit_cost
            
        recent_transactions = StockTransaction.objects.all().order_by('-created_at')[:10]
        
    elif request.user.role == 'store':
        if not request.user.inventory:
            messages.error(request, 'No inventory assigned')
            return redirect('common:dashboard')
        materials = RawMaterial.objects.filter(inventory=request.user.inventory)
        total_materials = materials.count()
        low_stock_count = materials.filter(current_stock__lte=F('minimum_stock')).count()
        pending_requests = StockRequest.objects.filter(inventory=request.user.inventory, status='pending').count()
        
        total_value = 0
        for material in materials:
            total_value += material.current_stock * material.unit_cost
            
        recent_transactions = StockTransaction.objects.filter(
            raw_material__inventory=request.user.inventory
        ).order_by('-created_at')[:10]
    else:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    context = {
        'total_materials': total_materials,
        'low_stock_count': low_stock_count,
        'pending_requests': pending_requests,
        'total_value': total_value,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def record_wastage(request):
    """Record wastage of raw materials"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        material_id = request.POST.get('raw_material')
        quantity = Decimal(request.POST.get('quantity', 0))
        reason = request.POST.get('reason')
        notes = request.POST.get('notes', '')
        
        material = get_object_or_404(RawMaterial, id=material_id)
        
        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than 0')
            return redirect('inventory:record_wastage')
        
        if quantity > material.current_stock:
            messages.error(request, f'Cannot record wastage. Only {material.current_stock} {material.unit} available.')
            return redirect('inventory:record_wastage')
        
        # Create wastage record
        WastageRecord.objects.create(
            raw_material=material,
            quantity=quantity,
            unit_cost=material.unit_cost,
            reason=reason,
            notes=notes,
            recorded_by=request.user
        )
        
        # Reduce stock
        material.current_stock -= quantity
        material.save()
        
        # Create stock transaction
        StockTransaction.objects.create(
            raw_material=material,
            transaction_type='wastage',
            quantity=quantity,
            unit_cost=material.unit_cost,
            reference_number=f"WASTE-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Wastage recorded. Reason: {reason}",
            created_by=request.user
        )
        
        messages.success(request, f'Wastage recorded for {material.name}')
        return redirect('inventory:wastage_list')
    
    materials = RawMaterial.objects.filter(is_active=True)
    return render(request, 'inventory/record_wastage.html', {'materials': materials})


@login_required
def wastage_list(request):
    """List all wastage records"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    wastages = WastageRecord.objects.all().order_by('-recorded_at')
    
    # Calculate total wastage cost
    total_wastage_cost = wastages.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    # Group by reason
    wastage_by_reason = wastages.values('reason').annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_cost')
    )
    
    # Group by material
    wastage_by_material = wastages.values('raw_material__name').annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_cost')
    ).order_by('-total_cost')[:10]
    
    context = {
        'wastages': wastages,
        'total_wastage_cost': total_wastage_cost,
        'wastage_by_reason': wastage_by_reason,
        'wastage_by_material': wastage_by_material,
    }
    return render(request, 'inventory/wastage_list.html', context)


@login_required
def wastage_report(request):
    """Wastage report with filters"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    reason = request.GET.get('reason')
    material_id = request.GET.get('material')
    
    wastages = WastageRecord.objects.all()
    
    if start_date:
        wastages = wastages.filter(recorded_at__date__gte=start_date)
    if end_date:
        wastages = wastages.filter(recorded_at__date__lte=end_date)
    if reason:
        wastages = wastages.filter(reason=reason)
    if material_id:
        wastages = wastages.filter(raw_material_id=material_id)
    
    total_quantity = wastages.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_cost = wastages.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
    
    # Daily breakdown
    daily_wastage = wastages.extra({'date': "DATE(recorded_at)"}).values('date').annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum('total_cost')
    ).order_by('-date')
    
    context = {
        'wastages': wastages,
        'total_quantity': total_quantity,
        'total_cost': total_cost,
        'daily_wastage': daily_wastage,
        'start_date': start_date,
        'end_date': end_date,
        'reasons': WastageRecord.WASTAGE_REASONS,
        'materials': RawMaterial.objects.filter(is_active=True),
    }
    return render(request, 'inventory/wastage_report.html', context)


@login_required
def add_stock_page(request, pk):
    """Page for adding stock"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    material = get_object_or_404(RawMaterial, id=pk)
    
    if request.method == 'POST':
        form = AddStockForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            total_cost = form.cleaned_data['total_cost']
            reference = form.cleaned_data['reference_number']
            notes = form.cleaned_data['notes']
            
            unit_cost = total_cost / quantity
            
            # Weighted average calculation
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
                reference_number=reference,
                notes=notes,
                created_by=request.user
            )
            
            messages.success(request, f'Added {quantity} {material.unit} of {material.name}')
            return redirect('inventory:stock_detail', pk=material.id)
    else:
        form = AddStockForm()
    
    return render(request, 'inventory/add_stock_page.html', {'form': form, 'material': material})


@login_required
def edit_transaction(request, pk):
    """Edit a transaction"""
    if request.user.role not in ['admin', 'store'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    transaction = get_object_or_404(StockTransaction, id=pk)
    material = transaction.raw_material
    
    if request.method == 'POST':
        try:
            # Use Decimal for precise calculations
            from decimal import Decimal, ROUND_HALF_UP
            
            new_quantity = Decimal(request.POST.get('quantity', '0'))
            new_total_cost = Decimal(request.POST.get('total_cost', '0'))
            new_unit_cost = Decimal(request.POST.get('unit_cost', '0'))
            new_reference = request.POST.get('reference_number', '')
            new_notes = request.POST.get('notes', '')
            
            if new_quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0')
                return redirect('inventory:edit_transaction', pk=pk)
            
            if new_total_cost <= 0:
                messages.error(request, 'Total cost must be greater than 0')
                return redirect('inventory:edit_transaction', pk=pk)
            
            old_quantity = transaction.quantity
            quantity_difference = new_quantity - old_quantity
            
            # Update material stock based on transaction type
            if transaction.transaction_type in ['purchase', 'adjustment']:
                material.current_stock += quantity_difference
            elif transaction.transaction_type in ['usage', 'wastage', 'transfer']:
                material.current_stock -= quantity_difference
            
            if material.current_stock < 0:
                messages.error(request, 'Cannot reduce stock below 0')
                return redirect('inventory:edit_transaction', pk=pk)
            
            # Recalculate weighted average cost for purchases
            if transaction.transaction_type == 'purchase':
                # Remove old transaction effect and add new effect
                old_total_value = (material.current_stock - quantity_difference) * material.unit_cost
                new_total_value = old_total_value + new_total_cost
                if material.current_stock > 0:
                    material.unit_cost = (new_total_value / material.current_stock).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    material.unit_cost = new_unit_cost
            
            material.save()
            
            # Update transaction with precise values
            transaction.quantity = new_quantity
            transaction.total_cost = new_total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            transaction.unit_cost = new_unit_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            transaction.reference_number = new_reference
            
            if new_notes:
                transaction.notes = f"{new_notes}\n[Edited on {timezone.now().strftime('%Y-%m-%d %H:%M')} by {request.user.get_full_name() or request.user.username}]"
            
            transaction.save()
            
            messages.success(request, 'Transaction updated successfully')
            return redirect('inventory:stock_detail', pk=material.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'inventory/edit_transaction.html', {'transaction': transaction})

# apps/inventory/views.py - Add these views

from datetime import date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .models import DailyStockRequest, DailyRequestItem, ProductionBatch, DispatchRecord, SystemConfig
from apps.restaurant.models import MenuItem

# ==================== STAFF: Daily Stock Request ====================
def has_inventory_access(user):
    """Check if user can access inventory management"""
    return user.role in ['admin', 'superadmin', 'store']



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
        
        daily_request.status = 'pending'
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
    """View single request details - staff or admin/store"""
    daily_request = get_object_or_404(DailyStockRequest, id=pk)
    
    # Staff can only see their own restaurant's requests
    if request.user.role == 'staff' and daily_request.restaurant != request.user.restaurant:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    return render(request, 'inventory/daily_request_detail.html', {'daily_request': daily_request})


# ==================== ADMIN: View All Requests ====================

@login_required
def all_requests_list(request):
    """Admin AND Store can view all daily requests"""
    # Allow admin, superadmin, AND store users
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


@login_required
def consolidated_summary(request):
    """Admin AND Store can see consolidated summary"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    selected_date = request.GET.get('date', date.today())
    
    requests = DailyStockRequest.objects.filter(
        request_date=selected_date,
        status__in=['pending', 'approved', 'processing']
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
    
    return render(request, 'inventory/consolidated_summary.html', {
        'consolidated': consolidated.values(),
        'selected_date': selected_date
    })

# ==================== PRODUCTION & DISPATCH ====================

@login_required
def add_production_batch(request):
    """Admin/Store adds production batch for a menu item"""
    if request.user.role not in ['admin', 'superadmin', 'store']:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        menu_item_id = request.POST.get('menu_item')
        quantity = Decimal(request.POST.get('quantity', 0))
        batch_number = request.POST.get('batch_number', '')
        notes = request.POST.get('notes', '')
        
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        
        batch = ProductionBatch.objects.create(
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
    """Admin/Store dispatch produced items to restaurant"""
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
        
        # Check if all items are fulfilled
        all_fulfilled = True
        for item in daily_request.items.all():
            if item.fulfilled_quantity < item.requested_quantity:
                all_fulfilled = False
                break
        
        daily_request.status = 'completed' if all_fulfilled else 'processing'
        daily_request.save()
        
        messages.success(request, f'Dispatch completed for {daily_request.restaurant.name}')
        return redirect('inventory:all_requests_list')
    
    return render(request, 'inventory/dispatch_form.html', {'daily_request': daily_request})