# apps/orders/forms.py
from django import forms

from apps.restaurant.models import MenuItem
from .models import Order, Payment, WasteRecord

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['table', 'order_type', 'notes']
        widgets = {
            'table': forms.Select(attrs={'class': 'form-select'}),
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_method']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
        }

class WasteForm(forms.ModelForm):
    class Meta:
        model = WasteRecord
        fields = ['menu_item', 'quantity', 'reason']
        widgets = {
            'menu_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['menu_item'].queryset = MenuItem.objects.filter(is_available=True)