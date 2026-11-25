from django import forms

from .models import Customer


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "company_name",
            "tin_number",
            "vat_number",
            "phone",
            "email",
            "address",
            "credit_limit",
        ]
        labels = {
            "name": "Contact Person / Customer Name",
            "company_name": "Company Name",
            "tin_number": "Tax Identification Number (TIN)",
            "vat_number": "VAT Registration Number",
            "credit_limit": "Credit Limit (ETB)",
        }
        help_texts = {
            "name": "Required. Enter the contact person's name, or the customer's name for an individual.",
            "company_name": "Optional. Fill this in for a company, garage, or business customer.",
            "tin_number": "Business or customer TIN, if applicable.",
            "vat_number": "VAT registration number, if applicable.",
            "credit_limit": "Enter 0 if the customer does not have an approved credit limit.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "company_name": forms.TextInput(attrs={"class": "form-input"}),
            "tin_number": forms.TextInput(attrs={"class": "form-input"}),
            "vat_number": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "address": forms.Textarea(attrs={"class": "form-textarea", "rows": 3}),
            "credit_limit": forms.NumberInput(attrs={"class": "form-input", "min": "0", "step": "0.01"}),
        }

    def clean_credit_limit(self):
        credit_limit = self.cleaned_data["credit_limit"]
        if credit_limit < 0:
            raise forms.ValidationError("Credit limit cannot be negative.")
        return credit_limit
