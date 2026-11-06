from django import forms
import uuid
from .models import Product, Category, CarMake, CarModel, Warehouse, Supplier

class ProductForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['compatibilities'].required = False
        self.fields['wholesale_price'].required = False
        self.fields['reorder_level'].required = False
        self.fields['sku'].required = False
        self.fields['cost_price'].required = False

        if not self.instance.pk:
            if not self.initial.get('reorder_level'):
                self.initial['reorder_level'] = 5
            if not self.initial.get('wholesale_price'):
                self.initial['wholesale_price'] = 0.0
            if not self.initial.get('cost_price'):
                self.initial['cost_price'] = 0.0

    def clean_wholesale_price(self):
        val = self.cleaned_data.get('wholesale_price')
        if val is None or val == '':
            return 0.0
        return float(val)

    def clean_cost_price(self):
        val = self.cleaned_data.get('cost_price')
        if val is None or val == '':
            return 0.0
        return float(val)

    def clean_reorder_level(self):
        val = self.cleaned_data.get('reorder_level')
        if val is None or val == '':
            return 5
        return int(val)

    def clean_sku(self):
        sku = self.cleaned_data.get('sku', '').strip()
        if not sku:
            # Auto-generate unique SKU if empty
            part_no = self.cleaned_data.get('part_number', '').strip()
            if part_no:
                base_sku = f"SKU-{part_no.replace(' ', '-').upper()}"
                # Check uniqueness
                existing = Product.objects.filter(sku=base_sku)
                if self.instance.pk:
                    existing = existing.exclude(pk=self.instance.pk)
                if not existing.exists():
                    return base_sku
            return f"SKU-{uuid.uuid4().hex[:8].upper()}"
        return sku

    class Meta:
        model = Product
        fields = [
            'part_number',
            'sku',
            'name',
            'brand',
            'manufacturer_brand',
            'is_genuine',
            'category',
            'unit_of_measure',
            'cost_price',
            'selling_price',
            'wholesale_price',
            'quantity',
            'reorder_level',
            'location',
            'shelf_bin',
            'purpose',
            'vehicle_application',
            'alternate_numbers',
            'image',
            'compatibilities',
        ]
        widgets = {
            'part_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 04465-02220'}),
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BRK-PAD-001 (auto-generated if empty)'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Front Brake Pads Set'}),
            'brand': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Toyota OEM, Denso, Bosch'}),
            'manufacturer_brand': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Advics Japan, Brembo Italy'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'unit_of_measure': forms.Select(attrs={'class': 'form-select'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'wholesale_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-input', 'min': '0'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Aisle A-01'}),
            'shelf_bin': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. A-01-02'}),
            'purpose': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Front Axle Friction Braking'}),
            'vehicle_application': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'e.g. Toyota Corolla (2007-2019) 1.6L/1.8L'}),
            'alternate_numbers': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 04465-YZZE1, D1210-8331'}),
            'compatibilities': forms.CheckboxSelectMultiple(),
        }
