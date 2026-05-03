# apps/orders/models.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid

class Order(models.Model):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )
    
    ORDER_TYPE = (
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True)
    restaurant = models.ForeignKey('restaurant.Restaurant', on_delete=models.CASCADE)
    table = models.ForeignKey('restaurant.Table', on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE, default='dine_in')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=20, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')], default='percentage')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.order_number} - {self.restaurant.name}"


class OrderItem(models.Model):
    ITEM_STATUS = (
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('served', 'Served'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=20, choices=ITEM_STATUS, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"


class Payment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile', 'Mobile Payment'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    received_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    received_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class KitchenPrint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    printed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    printed_at = models.DateTimeField(auto_now_add=True)


class WasteRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey('restaurant.Restaurant', on_delete=models.CASCADE)
    menu_item = models.ForeignKey('restaurant.MenuItem', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    reason = models.TextField()
    recorded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'waste_records'


# Optional: Signal to create SalesEntry when order is completed
@receiver(post_save, sender=Order)
def create_sales_entry_on_completion(sender, instance, created, **kwargs):
    """When an order is marked as completed, create a SalesEntry for each item"""
    if instance.status == 'completed' and instance.payment_status == 'paid':
        from apps.inventory.models import SalesEntry  # Avoid circular import
        for item in instance.items.all():
            SalesEntry.objects.get_or_create(
                restaurant=instance.restaurant,
                menu_item=item.menu_item,
                quantity_sold=item.quantity,
                sale_date=instance.created_at.date(),
                entered_by=instance.staff,
                defaults={'notes': f"Auto from order {instance.order_number}"}
            )