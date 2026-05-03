from django.contrib import admin
from apps.restaurant.models import Restaurant, Table, MenuCategory, MenuItem, Recipe, SetMenu, SetMenuItem


class SetMenuItemInline(admin.TabularInline):
    model = SetMenuItem
    extra = 2
    verbose_name = "Menu Item"
    verbose_name_plural = "Menu Items"

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('display_order', 'is_active')
    list_per_page = 20

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code', 'phone', 'email')
    list_per_page = 20

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'restaurant', 'capacity', 'status')
    list_filter = ('status', 'restaurant')
    search_fields = ('table_number', 'restaurant__name')
    list_per_page = 20

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'quantity', 'reorder_level', 'is_low_stock', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)
    list_editable = ('quantity', 'reorder_level', 'is_available')
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'image')
        }),
        ('Pricing', {
            'fields': ('price', 'cost')
        }),
        ('Stock Management', {
            'fields': ('quantity', 'reorder_level', 'is_available')
        }),
        ('Preparation', {
            'fields': ('preparation_time', 'has_recipe')
        }),
    )

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'raw_material', 'quantity_required', 'unit', 'wastage_percentage')
    list_filter = ('menu_item__category', 'unit')
    search_fields = ('menu_item__name', 'raw_material__name')
    list_per_page = 20

@admin.register(SetMenu)
class SetMenuAdmin(admin.ModelAdmin):
    list_display = ('name','discount_type', 'discount_value', 'start_date', 'end_date', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('name',)
    list_per_page = 20
    inlines = [SetMenuItemInline]
    

@admin.register(SetMenuItem)
class SetMenuItemAdmin(admin.ModelAdmin):
    list_display = ('set_menu', 'menu_item', 'quantity')
    list_filter = ('set_menu',)
    search_fields = ('set_menu__name', 'menu_item__name')
    list_per_page = 20