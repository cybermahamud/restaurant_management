# apps/orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem, Payment, WasteRecord, KitchenPrint

# apps/orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem, Payment, KitchenPrint

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price',)
    fields = ('menu_item', 'quantity', 'unit_price', 'total_price', 'status', 'notes')
    
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('amount', 'payment_method', 'received_amount', 'change_amount', 'received_by', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'restaurant', 'table', 'total_amount', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'order_type', 'created_at')
    search_fields = ('order_number', 'restaurant__name', 'table__table_number')
    readonly_fields = ('order_number', 'subtotal', 'tax_amount', 'total_amount', 'created_at', 'updated_at')
    list_per_page = 20
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'restaurant', 'table', 'staff', 'order_type')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Financial', {
            'fields': ('subtotal', 'discount_amount', 'discount_type', 'tax_amount', 'total_amount')
        }),
        ('Additional', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    
    inlines = [OrderItemInline, PaymentInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('restaurant', 'table', 'staff')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'menu_item', 'quantity', 'unit_price', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'menu_item__name')
    readonly_fields = ('total_price',)
    list_per_page = 20

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'payment_method', 'received_amount', 'change_amount', 'received_by', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('order__order_number', 'received_by__username')
    readonly_fields = ('created_at',)
    list_per_page = 20

@admin.register(KitchenPrint)
class KitchenPrintAdmin(admin.ModelAdmin):
    list_display = ('order', 'printed_by', 'printed_at')
    list_filter = ('printed_at',)
    search_fields = ('order__order_number', 'printed_by__username')
    readonly_fields = ('printed_at',)
    list_per_page = 20

@admin.register(WasteRecord)
class WasteRecordAdmin(admin.ModelAdmin):
    list_display = ('menu_item', 'restaurant', 'quantity', 'reason', 'recorded_at', 'recorded_by')
    list_filter = ('recorded_at', 'restaurant')
    search_fields = ('menu_item__name', 'reason')
    list_per_page = 20