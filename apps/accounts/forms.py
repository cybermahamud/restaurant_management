# apps/accounts/forms.py - Update UserCreateForm
from django import forms
from .models import User, Employee
from apps.restaurant.models import Restaurant
from apps.inventory.models import Inventory

class UserLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'restaurant', 'inventory', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'restaurant': forms.Select(attrs={'class': 'form-select'}),
            'inventory': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['restaurant'].queryset = Restaurant.objects.filter(is_active=True)
        self.fields['inventory'].queryset = Inventory.objects.filter(is_active=True)
        self.fields['restaurant'].required = False
        self.fields['inventory'].required = False
        self.fields['is_active'].initial = True
        self.fields['password'].required = True
        self.fields['confirm_password'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        role = cleaned_data.get('role')
        restaurant = cleaned_data.get('restaurant')
        inventory = cleaned_data.get('inventory')
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters")
        
        if role == 'staff' and not restaurant:
            raise forms.ValidationError("Staff users must be assigned to a restaurant")
        
        if role == 'store' and not inventory:
            raise forms.ValidationError("Store users must be assigned to an inventory")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'role', 'restaurant', 'inventory', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'restaurant': forms.Select(attrs={'class': 'form-select'}),
            'inventory': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['restaurant'].queryset = Restaurant.objects.filter(is_active=True)
        self.fields['inventory'].queryset = Inventory.objects.filter(is_active=True)
        self.fields['restaurant'].required = False
        self.fields['inventory'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        restaurant = cleaned_data.get('restaurant')
        inventory = cleaned_data.get('inventory')
        
        if role == 'staff' and not restaurant:
            raise forms.ValidationError("Staff users must be assigned to a restaurant")
        
        if role == 'store' and not inventory:
            raise forms.ValidationError("Store users must be assigned to an inventory")
        
        return cleaned_data


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['employee_id', 'name', 'email', 'phone', 'address', 'position', 
                  'department', 'employment_type', 'restaurant', 'inventory', 
                  'salary', 'hire_date', 'is_active']
        widgets = {
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'employment_type': forms.Select(attrs={'class': 'form-select'}),
            'restaurant': forms.Select(attrs={'class': 'form-select'}),
            'inventory': forms.Select(attrs={'class': 'form-select'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['restaurant'].queryset = Restaurant.objects.filter(is_active=True)
        self.fields['inventory'].queryset = Inventory.objects.filter(is_active=True)
        self.fields['restaurant'].required = False
        self.fields['inventory'].required = False


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password != confirm_password:
            raise forms.ValidationError("New passwords do not match")
        
        if len(new_password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters")
        
        return cleaned_data


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        if len(new_password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters")
        
        return cleaned_data