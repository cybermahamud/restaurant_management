# apps/inventory/forms.py
from django import forms
from decimal import Decimal
from .models import (
    RawMaterial, RawMaterialCategory, Inventory,
    DailyStockRequest, ProductionBatch, DispatchRecord
)
from apps.restaurant.models import MenuItem


class RawMaterialCategoryForm(forms.ModelForm):
    class Meta:
        model = RawMaterialCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ['name', 'location', 'manager_name', 'phone', 'email', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'manager_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RawMaterialForm(forms.ModelForm):
    class Meta:
        model = RawMaterial
        fields = ['name', 'sku', 'category', 'unit', 'minimum_stock', 'maximum_stock', 
                  'reorder_level', 'unit_cost', 'inventory', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'maximum_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'inventory': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = RawMaterialCategory.objects.all()
        self.fields['inventory'].queryset = Inventory.objects.filter(is_active=True)


class AddStockForm(forms.Form):
    quantity = forms.DecimalField(
        max_digits=10, decimal_places=3, min_value=0.001,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'e.g., 50'}),
        label='Quantity'
    )
    total_cost = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'e.g., 5000'}),
        label='Total Cost'
    )
    reference_number = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Invoice # or Bill #'})
    )
    notes = forms.CharField(
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any notes about this purchase'})
    )


class UpdateStockForm(forms.Form):
    new_quantity = forms.DecimalField(
        max_digits=10, decimal_places=3, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    new_unit_cost = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    reason = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Reason for adjustment'})
    )


class DailyRequestForm(forms.ModelForm):
    class Meta:
        model = DailyStockRequest
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Add any special instructions or notes...'
            })
        }


class ProductionBatchForm(forms.ModelForm):
    class Meta:
        model = ProductionBatch
        fields = ['batch_number', 'quantity_produced', 'notes']
        widgets = {
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., BATCH-001'
            }),
            'quantity_produced': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Enter produced quantity'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any notes about this batch...'
            }),
        }
    
    def clean_batch_number(self):
        batch_number = self.cleaned_data.get('batch_number')
        if ProductionBatch.objects.filter(batch_number=batch_number).exists():
            raise forms.ValidationError("Batch number already exists. Please use a unique batch number.")
        return batch_number
    
    def clean_quantity_produced(self):
        quantity = self.cleaned_data.get('quantity_produced')
        if quantity <= 0:
            raise forms.ValidationError("Quantity produced must be greater than zero.")
        return quantity


class DispatchForm(forms.ModelForm):
    class Meta:
        model = DispatchRecord
        fields = ['quantity', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Enter dispatch quantity'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Any notes about this dispatch...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.max_quantity = kwargs.pop('max_quantity', None)
        super().__init__(*args, **kwargs)
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError("Dispatch quantity must be greater than zero.")
        if self.max_quantity and quantity > self.max_quantity:
            raise forms.ValidationError(f"Dispatch quantity cannot exceed {self.max_quantity}.")
        return quantity