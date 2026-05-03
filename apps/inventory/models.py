# apps/inventory/models.py
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class RawMaterialCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'raw_material_categories'
        verbose_name_plural = "Raw Material Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    manager_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventories'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.location}"


class RawMaterial(models.Model):
    UNIT_CHOICES = (
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('L', 'Liter'),
        ('ml', 'Milliliter'),
        ('pcs', 'Pieces'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('bottle', 'Bottle'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(RawMaterialCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='materials')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    current_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    maximum_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='raw_materials')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'raw_materials'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('purchase', 'Purchase'),
        ('usage', 'Usage'),
        ('wastage', 'Wastage'),
        ('transfer', 'Transfer'),
        ('adjustment', 'Adjustment'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(0.001)])
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_transactions'
        ordering = ['-created_at']


class StockRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('fulfilled', 'Fulfilled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('restaurant.Restaurant', on_delete=models.CASCADE, related_name='stock_requests')
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name='stock_requests')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE, related_name='stock_requests')
    quantity_requested = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'stock_requests'
        ordering = ['-requested_at']


# ==================== NEW WORKFLOW MODELS (No ProductionPlan) ====================

class DailyStockRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('restaurant.Restaurant', on_delete=models.CASCADE, related_name='daily_requests')
    request_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_stock_requests'
        unique_together = ['restaurant', 'request_date']
        ordering = ['-request_date']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.request_date}"


class DailyRequestItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_request = models.ForeignKey(DailyStockRequest, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE)
    requested_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fulfilled_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'daily_request_items'
        unique_together = ['daily_request', 'menu_item']


class ProductionBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE)
    batch_number = models.CharField(max_length=50, unique=True)
    quantity_produced = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    produced_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    produced_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'production_batches'
        ordering = ['-produced_at']


class DispatchRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_request = models.ForeignKey(DailyStockRequest, on_delete=models.CASCADE, related_name='dispatches')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE)
    production_batch = models.ForeignKey(ProductionBatch, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    dispatched_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dispatch_records'
        ordering = ['-dispatched_at']