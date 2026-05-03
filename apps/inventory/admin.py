# apps/inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    RawMaterialCategory, Inventory, RawMaterial, StockTransaction, StockRequest,
    DailyStockRequest, DailyRequestItem, ProductionBatch, DispatchRecord
)


@admin.register(RawMaterialCategory)
class RawMaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)
    list_per_page = 20


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'manager_name', 'phone', 'email', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'location', 'manager_name')
    list_per_page = 20


@admin.register(RawMaterial)
class RawMaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'unit', 'current_stock', 'minimum_stock', 'unit_cost', 'inventory', 'is_active')
    list_filter = ('category', 'unit', 'inventory', 'is_active')
    search_fields = ('name', 'sku')
    list_per_page = 20
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'sku', 'category', 'unit')
        }),
        ('Stock Levels', {
            'fields': ('current_stock', 'minimum_stock', 'maximum_stock', 'reorder_level')
        }),
        ('Cost Information', {
            'fields': ('unit_cost', 'inventory')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('raw_material', 'transaction_type', 'quantity', 'unit_cost', 'total_cost', 'created_at', 'created_by')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('raw_material__name', 'reference_number')
    readonly_fields = ('total_cost', 'created_at')
    list_per_page = 20


@admin.register(StockRequest)
class StockRequestAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'menu_item', 'quantity_requested', 'status', 'requested_at')
    list_filter = ('status', 'requested_at')
    search_fields = ('restaurant__name', 'menu_item__name')
    list_per_page = 20


@admin.register(DailyStockRequest)
class DailyStockRequestAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'request_date', 'status_badge', 'items_count', 'created_at')
    list_filter = ('status', 'request_date')
    search_fields = ('restaurant__name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 20
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'processing': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
        }
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            colors.get(obj.status, 'secondary'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Items'


@admin.register(DailyRequestItem)
class DailyRequestItemAdmin(admin.ModelAdmin):
    list_display = ('daily_request', 'menu_item', 'requested_quantity', 'fulfilled_quantity')
    list_filter = ('daily_request__request_date',)
    search_fields = ('menu_item__name',)


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ('batch_number', 'menu_item', 'quantity_produced', 'produced_by', 'produced_at')
    list_filter = ('produced_at',)
    search_fields = ('batch_number', 'menu_item__name')
    list_per_page = 20


@admin.register(DispatchRecord)
class DispatchRecordAdmin(admin.ModelAdmin):
    list_display = ('daily_request', 'menu_item', 'quantity', 'dispatched_by', 'dispatched_at')
    list_filter = ('dispatched_at',)
    search_fields = ('daily_request__restaurant__name', 'menu_item__name')
    list_per_page = 20