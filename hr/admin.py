from django.contrib import admin
from .models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'employee_id', 'role', 'hire_date', 'salary')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
