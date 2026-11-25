from django import forms

from inventory.models import Purchase

from .models import SupplierPayment


class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = (
            "supplier",
            "purchase",
            "amount",
            "payment_date",
            "payment_method",
            "reference",
            "notes",
        )
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["purchase"].queryset = (
            Purchase.objects.filter(supplier__isnull=False).select_related("supplier").order_by("-date")
        )
        self.fields["purchase"].required = False

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        purchase = cleaned_data.get("purchase")
        supplier = cleaned_data.get("supplier")
        if purchase and supplier and purchase.supplier_id != supplier.pk:
            self.add_error("purchase", "Choose a purchase belonging to the selected supplier.")
        return cleaned_data
