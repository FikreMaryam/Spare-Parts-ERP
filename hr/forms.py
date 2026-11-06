from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from .models import Employee

class EmployeeForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password = forms.CharField(widget=forms.PasswordInput(render_value=False), required=False, help_text="Leave blank to keep the current password.")

    class Meta:
        model = Employee
        fields = ['employee_id', 'phone', 'address', 'salary', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            # If editing, password is not required
            self.fields['password'].required = False
        else:
            # If creating, password is required
            self.fields['password'].required = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            user_qs = user_qs.exclude(pk=self.instance.user.pk)
        if user_qs.exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def save(self, commit=True):
        with transaction.atomic():
            # Get or create the User instance
            if self.instance and self.instance.pk:
                user = self.instance.user
            else:
                user = User()

            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data.get('email', '')
            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            
            # Set is_staff based on role
            role = self.cleaned_data.get('role')
            if role in ['ADMIN', 'MANAGER']:
                user.is_staff = True
            else:
                user.is_staff = False
                
            password = self.cleaned_data.get('password')
            if password:
                user.set_password(password)

            user.save()

            employee = super().save(commit=False)
            employee.user = user

            if commit:
                employee.save()
            return employee
