# apps/restaurant/views.py
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.utils import timezone
from .models import Restaurant, Table, MenuItem, SetMenu, Recipe, MenuCategory
from .forms import RestaurantForm, TableForm, MenuItemForm, SetMenuForm, RecipeForm, MenuCategoryForm
from apps.inventory.models import Inventory, RawMaterial, StockRequest, StockTransaction
from apps.common.decorators import role_required

@login_required
def restaurant_list(request):
    """List all restaurants - admin sees all, staff sees their own"""
    if request.user.role == 'admin':
        restaurants = Restaurant.objects.all()
    elif request.user.role in ['staff', 'manager'] and request.user.restaurant:
        restaurants = Restaurant.objects.filter(id=request.user.restaurant.id)
    else:
        restaurants = Restaurant.objects.filter(is_active=True)
    
    paginator = Paginator(restaurants, 10)
    page = request.GET.get('page')
    restaurants = paginator.get_page(page)
    return render(request, 'restaurant/list.html', {'restaurants': restaurants})

@login_required
def create_restaurant(request):
    """Create restaurant - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can create restaurants.')
        return redirect('restaurant:list')
    
    if request.method == 'POST':
        form = RestaurantForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Restaurant created successfully')
            return redirect('restaurant:list')
    else:
        form = RestaurantForm()
    
    return render(request, 'restaurant/form.html', {'form': form})

@login_required
def edit_restaurant(request, pk):
    """Edit restaurant - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can edit restaurants.')
        return redirect('restaurant:list')
    
    restaurant = get_object_or_404(Restaurant, id=pk)
    if request.method == 'POST':
        form = RestaurantForm(request.POST, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Restaurant updated successfully')
            return redirect('restaurant:list')
    else:
        form = RestaurantForm(instance=restaurant)
    
    return render(request, 'restaurant/form.html', {'form': form})

@login_required
def delete_restaurant(request, pk):
    """Delete restaurant - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete restaurants.')
        return redirect('restaurant:list')
    
    restaurant = get_object_or_404(Restaurant, id=pk)
    restaurant.delete()
    messages.success(request, 'Restaurant deleted successfully')
    return redirect('restaurant:list')

@login_required
def manage_tables(request, restaurant_id):
    """Manage tables - admin can manage any, staff only their restaurant"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    # Check permission
    if request.user.role != 'admin' and request.user.restaurant != restaurant:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    tables = Table.objects.filter(restaurant=restaurant)
    
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save(commit=False)
            table.restaurant = restaurant
            table.save()
            messages.success(request, f'Table {table.table_number} added successfully')
            return redirect('restaurant:manage_tables', restaurant_id=restaurant.id)
    else:
        form = TableForm()
    
    return render(request, 'restaurant/tables.html', {
        'restaurant': restaurant,
        'tables': tables,
        'form': form
    })

@login_required
def update_table_status(request, table_id):
    """Update table status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    table = get_object_or_404(Table, id=table_id)
    status = request.POST.get('status')
    
    table.status = status
    table.save()
    
    return JsonResponse({'success': True, 'message': f'Table status updated to {status}'})

@login_required
def update_table(request, table_id):
    """Update table details"""
    table = get_object_or_404(Table, id=table_id)
    
    if request.method == 'POST':
        table.table_number = request.POST.get('table_number')
        table.capacity = request.POST.get('capacity')
        table.section = request.POST.get('section')
        table.status = request.POST.get('status')
        table.save()
        
        messages.success(request, f'Table {table.table_number} updated successfully')
        return redirect('restaurant:manage_tables', restaurant_id=table.restaurant.id)
    
    return redirect('restaurant:manage_tables', restaurant_id=table.restaurant.id)

@login_required
def delete_table(request, pk):
    """Delete table - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete tables.')
        return redirect('common:dashboard')
    
    table = get_object_or_404(Table, id=pk)
    restaurant_id = table.restaurant.id
    table.delete()
    messages.success(request, 'Table deleted successfully')
    return redirect('restaurant:manage_tables', restaurant_id=restaurant_id)

@login_required
def menu_list(request):
    """List all menu items"""
    if request.user.role not in ['admin', 'manager', 'staff'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    menu_items = MenuItem.objects.all().order_by('category__name', 'name')
    categories = MenuCategory.objects.all().order_by('name')
    
    context = {
        'menu_items': menu_items,
        'categories': categories,
    }
    return render(request, 'restaurant/menu_list.html', context)

@login_required
def create_menu_item(request):
    """Create new menu item"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('restaurant:menu_list')
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu_item = form.save()
            messages.success(request, f'Menu item "{menu_item.name}" created successfully')
            return redirect('restaurant:menu_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MenuItemForm()
    
    categories = MenuCategory.objects.filter(is_active=True)
    return render(request, 'restaurant/menu_form.html', {
        'form': form,
        'categories': categories,
        'title': 'Add Menu Item'
    })

@login_required
def edit_menu_item(request, pk):
    """Edit menu item"""
    if request.user.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('restaurant:menu_list')
    
    menu_item = get_object_or_404(MenuItem, id=pk)
    
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            form.save()
            messages.success(request, f'Menu item "{menu_item.name}" updated successfully')
            return redirect('restaurant:menu_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = MenuItemForm(instance=menu_item)
    
    categories = MenuCategory.objects.filter(is_active=True)
    return render(request, 'restaurant/menu_form.html', {
        'form': form,
        'menu_item': menu_item,
        'categories': categories,
        'title': 'Edit Menu Item'
    })

@login_required
def delete_menu_item(request, pk):
    """Delete menu item - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete menu items.')
        return redirect('restaurant:menu_list')
    
    menu_item = get_object_or_404(MenuItem, id=pk)
    menu_item.delete()
    messages.success(request, 'Menu item deleted successfully')
    return redirect('restaurant:menu_list')

@login_required
def manage_recipes(request, menu_item_id):
    """Manage recipes - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can manage recipes.')
        return redirect('restaurant:menu_list')
    
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    recipes = Recipe.objects.filter(menu_item=menu_item)
    
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.menu_item = menu_item
            recipe.save()
            menu_item.has_recipe = True
            menu_item.save()
            messages.success(request, 'Recipe added successfully')
            return redirect('restaurant:manage_recipes', menu_item_id=menu_item.id)
    else:
        form = RecipeForm()
    
    return render(request, 'restaurant/recipes.html', {
        'menu_item': menu_item,
        'recipes': recipes,
        'form': form
    })

@login_required
def delete_recipe(request, pk):
    """Delete recipe - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete recipes.')
        return redirect('restaurant:menu_list')
    
    recipe = get_object_or_404(Recipe, id=pk)
    menu_item_id = recipe.menu_item.id
    recipe.delete()
    
    if not Recipe.objects.filter(menu_item_id=menu_item_id).exists():
        menu_item = get_object_or_404(MenuItem, id=menu_item_id)
        menu_item.has_recipe = False
        menu_item.save()
    
    messages.success(request, 'Recipe deleted successfully')
    return redirect('restaurant:manage_recipes', menu_item_id=menu_item_id)

from django.utils import timezone
@login_required
def set_menu_list(request):
    """List set menus - all authenticated users"""
    set_menus = SetMenu.objects.all().prefetch_related(
        'setmenuitem_set__menu_item'
    ).order_by('-is_active', 'name')
    
    paginator = Paginator(set_menus, 10)
    page = request.GET.get('page')
    set_menus = paginator.get_page(page)
    
    context = {
        'set_menus': set_menus,
        'now': timezone.now(),
    }
    return render(request, 'restaurant/set_menu_list.html', context)

@login_required
def create_set_menu(request):
    """Create set menu - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can create set menus.')
        return redirect('restaurant:set_menu_list')
    
    if request.method == 'POST':
        form = SetMenuForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Set menu created successfully')
            return redirect('restaurant:set_menu_list')
    else:
        form = SetMenuForm()
    
    return render(request, 'restaurant/set_menu_form.html', {'form': form})

@login_required
def delete_set_menu(request, pk):
    """Delete set menu - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete set menus.')
        return redirect('restaurant:set_menu_list')
    
    set_menu = get_object_or_404(SetMenu, id=pk)
    set_menu.delete()
    messages.success(request, 'Set menu deleted successfully')
    return redirect('restaurant:set_menu_list')


@login_required
def edit_set_menu(request, pk):
    """Edit set menu - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can edit set menus.')
        return redirect('restaurant:set_menu_list')
    
    set_menu = get_object_or_404(SetMenu, id=pk)
    
    if request.method == 'POST':
        form = SetMenuForm(request.POST, instance=set_menu)
        if form.is_valid():
            form.save()
            messages.success(request, 'Set menu updated successfully')
            return redirect('restaurant:set_menu_list')
    else:
        form = SetMenuForm(instance=set_menu)
    
    return render(request, 'restaurant/set_menu_form.html', {'form': form, 'title': 'Edit Set Menu'})


from .models import MenuCategory
from .forms import MenuCategoryForm

@login_required
def category_list(request):
    """List menu categories"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    categories = MenuCategory.objects.all()
    return render(request, 'restaurant/category_list.html', {'categories': categories})

@login_required
def create_category(request):
    """Create menu category"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    if request.method == 'POST':
        form = MenuCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created successfully')
            return redirect('restaurant:category_list')
    else:
        form = MenuCategoryForm()
    
    return render(request, 'restaurant/category_form.html', {'form': form})

@login_required
def edit_category(request, pk):
    """Edit menu category"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    category = get_object_or_404(MenuCategory, id=pk)
    if request.method == 'POST':
        form = MenuCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully')
            return redirect('restaurant:category_list')
    else:
        form = MenuCategoryForm(instance=category)
    
    return render(request, 'restaurant/category_form.html', {'form': form})

@login_required
def delete_category(request, pk):
    """Delete menu category - admin only"""
    if request.user.role != 'admin':
        messages.error(request, 'Access denied. Only administrators can delete categories.')
        return redirect('restaurant:category_list')
    
    category = get_object_or_404(MenuCategory, id=pk)
    
    # Check if category has items
    if category.items.count() > 0:
        messages.error(request, f'Cannot delete category "{category.name}" because it has {category.items.count()} menu items.')
        return redirect('restaurant:category_list')
    
    category.delete()
    messages.success(request, f'Category "{category.name}" deleted successfully')
    return redirect('restaurant:category_list')


@login_required
def stock_status(request):
    """View stock status for restaurant staff"""
    
    # Check permission
    if request.user.role not in ['staff', 'manager', 'admin'] and not request.user.is_superuser:
        messages.error(request, 'Access denied')
        return redirect('common:dashboard')
    
    # Get restaurant
    if request.user.is_superuser or request.user.role == 'admin':
        restaurant = Restaurant.objects.first()
    else:
        restaurant = request.user.restaurant
    
    if not restaurant:
        messages.error(request, 'No restaurant found')
        return redirect('common:dashboard')
    
    # Get all menu items with stock info
    menu_items = MenuItem.objects.filter(is_available=True).order_by('name')
    
    # Prepare stock status data
    stock_status = []
    for item in menu_items:
        stock_status.append({
            'menu_item': item,
            'quantity': item.quantity,
            'reorder_level': item.reorder_level,
        })
    
    # Get recent stock requests
    recent_requests = StockRequest.objects.filter(
        restaurant=restaurant
    ).order_by('-requested_at')[:10]
    
    context = {
        'restaurant': restaurant,
        'stock_status': stock_status,
        'recent_requests': recent_requests,
    }
    return render(request, 'restaurant/stock_status.html', context)


@login_required
def create_stock_request_ajax(request):
    """Create stock request via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)
    
    # Check permission - only staff, manager, admin can request
    if request.user.role not in ['staff', 'manager', 'admin'] and not request.user.is_superuser:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Check if user has a restaurant assigned
    if not request.user.restaurant:
        return JsonResponse({'error': 'No restaurant assigned'}, status=400)
    
    menu_item_id = request.POST.get('menu_item_id')
    quantity = request.POST.get('quantity', 0)
    notes = request.POST.get('notes', '')
    
    if not menu_item_id or int(quantity) <= 0:
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    
    # Get the central inventory (first active inventory)
    from apps.inventory.models import Inventory
    inventory = Inventory.objects.filter(is_active=True).first()
    
    if not inventory:
        return JsonResponse({'error': 'No inventory available. Contact administrator.'}, status=400)
    
    # Create stock request
    stock_request = StockRequest.objects.create(
        restaurant=request.user.restaurant,
        inventory=inventory,
        menu_item=menu_item,
        quantity_requested=int(quantity),
        status='pending',
        notes=notes
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Stock request for {quantity} x {menu_item.name} sent to inventory manager'
    })
