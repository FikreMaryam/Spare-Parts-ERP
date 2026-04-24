from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django_tenants.utils import tenant_context
from .forms import TenantForm
from .models import Domain
from customers.models import Client  # Assuming Client is the tenant model

from django.core import signing
from django.urls import reverse

def landing_page(request):
    return render(request, 'customers/landing.html')

def register_tenant(request):
    if request.method == 'POST':
        form = TenantForm(request.POST)
        if form.is_valid():
            tenant = form.save(commit=False)
            tenant.schema_name = form.cleaned_data['domain_prefix']
            tenant.save() # creates schema

            domain = Domain()
            domain.domain = f"{form.cleaned_data['domain_prefix']}.localhost"
            domain.tenant = tenant
            domain.is_primary = True
            domain.save()

            # Create the initial admin user in the new tenant schema
            User = get_user_model()
            with tenant_context(tenant):
                User.objects.create_superuser(
                    username=form.cleaned_data['admin_username'],
                    email=form.cleaned_data['admin_email'],
                    password=form.cleaned_data['admin_password']
                )

            return redirect(f"http://{domain.domain}:8000/login/")
    else:
        form = TenantForm()
    
    return render(request, 'customers/register.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def saas_dashboard(request):
    tenants = Client.objects.exclude(schema_name='public')
    tenant_data = []
    User = get_user_model()
    
    for tenant in tenants:
        with tenant_context(tenant):
            users = list(User.objects.all().values('id', 'username', 'email', 'is_active', 'is_staff'))
            
        domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
        tenant_data.append({
            'tenant': tenant,
            'domain': domain.domain if domain else None,
            'users': users
        })
        
    return render(request, 'customers/saas_dashboard.html', {'tenant_data': tenant_data})

@user_passes_test(lambda u: u.is_superuser)
def impersonate_generate_token(request, tenant_id, user_id):
    tenant = get_object_or_404(Client, id=tenant_id)
    domain = Domain.objects.filter(tenant=tenant, is_primary=True).first()
    
    if not domain:
        return redirect('saas_dashboard')
        
    # Generate a secure token valid for 5 minutes
    token = signing.dumps({'user_id': user_id, 'tenant_id': tenant.id}, salt='impersonate')
    
    # Construct the URL for the tenant
    tenant_url = f"http://{domain.domain}:8000/impersonate/auth/?token={token}"
    return redirect(tenant_url)
