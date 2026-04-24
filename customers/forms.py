from django import forms
from .models import Client, Domain

class TenantForm(forms.ModelForm):
    domain_prefix = forms.CharField(max_length=64, help_text="e.g. my-shop")
    admin_username = forms.CharField(max_length=150, help_text="Username for the shop admin")
    admin_email = forms.EmailField(help_text="Email for the shop admin")
    admin_password = forms.CharField(widget=forms.PasswordInput, help_text="Password for the shop admin")

    class Meta:
        model = Client
        fields = ['name']

    def clean_domain_prefix(self):
        prefix = self.cleaned_data['domain_prefix'].lower()
        if prefix == 'public':
            raise forms.ValidationError("This workspace name is reserved.")
        if Client.objects.filter(schema_name=prefix).exists():
            raise forms.ValidationError("This workspace name is already taken.")
        if Domain.objects.filter(domain=f"{prefix}.localhost").exists():
            raise forms.ValidationError("This subdomain is already taken.")
        return prefix
