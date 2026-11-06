from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView
from core.permissions import AdminRequiredMixin, admin_required
from .models import Employee
from .forms import EmployeeForm

@login_required
@admin_required
def employee_list(request):
    employees = Employee.objects.select_related('user').all()
    return render(request, 'hr/employee_list.html', {'employees': employees})

class EmployeeCreateView(AdminRequiredMixin, CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('employee_list')

class EmployeeUpdateView(AdminRequiredMixin, UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'generic_form.html'
    success_url = reverse_lazy('employee_list')

class EmployeeDeleteView(AdminRequiredMixin, DeleteView):
    model = Employee
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('employee_list')
