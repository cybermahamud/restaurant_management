# apps/restaurant/models.py
from django.db import models
from django.core.validators import MinValueValidator
import uuid
from django.contrib import messages

class Restaurant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    tax_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'restaurants'

    def __str__(self):
        return self.name


class Table(models.Model):
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('reserved', 'Reserved'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='tables')
    table_number = models.IntegerField()
    capacity = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')

    class Meta:
        db_table = 'tables'
        unique_together = ['restaurant', 'table_number']

    def __str__(self):
        return f"Table {self.table_number}"


class MenuCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'menu_categories'
        ordering = ['display_order', 'name']
        verbose_name_plural = "Menu Categories"

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE, related_name='items')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    preparation_time = models.IntegerField(help_text="Preparation time in minutes")
    is_available = models.BooleanField(default=True)
    has_recipe = models.BooleanField(default=False)
    quantity = models.IntegerField(default=0, help_text="Current stock quantity available")
    reorder_level = models.IntegerField(default=10, help_text="Alert when stock goes below this level")
    image = models.ImageField(upload_to='menu_items/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_items'
        ordering = ['category__display_order', 'name']

    def __str__(self):
        return f"{self.name} - ${self.price}"

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level

    @property
    def profit_margin(self):
        if self.cost > 0:
            return ((self.price - self.cost) / self.price) * 100
        return 0


class Recipe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='recipes')
    raw_material = models.ForeignKey('inventory.RawMaterial', on_delete=models.CASCADE)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20)
    wastage_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        db_table = 'recipes'
        unique_together = ['menu_item', 'raw_material']


class SetMenu(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    menu_items = models.ManyToManyField(MenuItem, through='SetMenuItem')
    discount_type = models.CharField(max_length=20, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'set_menus'

    @property
    def total_price(self):
        """Calculate total price of all items in set menu"""
        total = 0
        for item in self.setmenuitem_set.all():
            total += item.menu_item.price * item.quantity
        return total

    @property
    def discounted_price(self):
        """Calculate discounted price based on discount type and value"""
        total = self.total_price
        
        if self.discount_type == 'percentage':
            discount_amount = total * (self.discount_value / 100)
            return total - discount_amount
        elif self.discount_type == 'fixed':
            return max(0, total - self.discount_value)
        return total
    
    @property
    def savings(self):
        """Calculate total savings"""
        return self.total_price - self.discounted_price
    
    @property
    def savings_percentage(self):
        """Calculate savings percentage"""
        if self.total_price > 0:
            return (self.savings / self.total_price) * 100
        return 0

    def __str__(self):
        return f"{self.name} - ${self.discounted_price}"


class SetMenuItem(models.Model):
    set_menu = models.ForeignKey(SetMenu, on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    class Meta:
        db_table = 'set_menu_items'
        unique_together = ['set_menu', 'menu_item']