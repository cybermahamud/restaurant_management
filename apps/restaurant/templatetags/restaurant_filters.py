# apps/restaurant/templatetags/restaurant_filters.py
from django import template
from django.db.models import Sum, F
from decimal import Decimal

register = template.Library()

@register.filter
def sum_prices(set_menu_items):
    """Calculate total price of all items in set menu"""
    total = Decimal('0.00')
    for item in set_menu_items:
        total += item.menu_item.price * item.quantity
    return total

@register.filter
def calculate_discounted_price(set_menu):
    """Calculate discounted price based on discount type and value"""
    # Calculate total price first
    total = Decimal('0.00')
    for item in set_menu.setmenuitem_set.all():
        total += item.menu_item.price * item.quantity
    
    # Apply discount
    if set_menu.discount_type == 'percentage':
        discount_amount = total * (set_menu.discount_value / Decimal('100.00'))
        return total - discount_amount
    elif set_menu.discount_type == 'fixed':
        return max(Decimal('0.00'), total - set_menu.discount_value)
    return total

@register.filter
def subtract(value, arg):
    """Subtract two values"""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except:
        return Decimal('0.00')