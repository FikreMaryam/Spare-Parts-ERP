from django import forms
from .models import Expense
from django.utils import timezone

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Electricity Bill, Shop Rent, Staff Salary'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date') and not self.instance.pk:
            self.initial['date'] = timezone.now().date().isoformat()
