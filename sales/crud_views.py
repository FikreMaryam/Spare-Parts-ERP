from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from core.permissions import AdminRequiredMixin, SalesOrAdminRequiredMixin
from .forms import CustomerForm
from .models import Customer

# Customer (Sales can Edit/Add, Admin can Delete)
class CustomerCreateView(SalesOrAdminRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('customer_list')

class CustomerUpdateView(SalesOrAdminRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('customer_list')

class CustomerDeleteView(AdminRequiredMixin, DeleteView):
    model = Customer
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('customer_list')
