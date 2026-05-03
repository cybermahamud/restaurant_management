# apps/restaurant/forms.py
from django import forms
from .models import Restaurant, Table, MenuItem, SetMenu, Recipe, MenuCategory
from apps.inventory.models import RawMaterial

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = '__all__'
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'created_at': forms.DateInput(attrs={'type': 'date'}),
        }

class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number', 'capacity', 'status']  # Remove 'section' field
        widgets = {
            'table_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['table_number'].label = "Table Number"
        self.fields['capacity'].label = "Capacity (persons)"
        self.fields['status'].label = "Status"

class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ['name', 'description', 'display_order', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'class': 'form-control'})
        self.fields['description'].widget.attrs.update({'class': 'form-control'})

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['name', 'description', 'category', 'price', 'cost', 'preparation_time', 
                  'has_recipe', 'is_available', 'quantity', 'reorder_level', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'step': '0.01'}),
            'cost': forms.NumberInput(attrs={'step': '0.01'}),
            'preparation_time': forms.NumberInput(attrs={'min': 0}),
            'quantity': forms.NumberInput(attrs={'min': 0}),
            'reorder_level': forms.NumberInput(attrs={'min': 0}),
        }

class SetMenuForm(forms.ModelForm):
    class Meta:
        model = SetMenu
        fields = '__all__'
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discount_type'].widget.attrs.update({'class': 'form-select'})

class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['raw_material', 'quantity_required', 'unit', 'wastage_percentage']
        widgets = {
            'quantity_required': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'wastage_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['raw_material'].queryset = RawMaterial.objects.all()
        self.fields['raw_material'].widget.attrs.update({'class': 'form-select'})
        self.fields['unit'].widget.attrs.update({'class': 'form-control'})