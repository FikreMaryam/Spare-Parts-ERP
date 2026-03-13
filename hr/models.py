from django.db import models
from django.contrib.auth.models import User

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=10, unique=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    hire_date = models.DateField(auto_now_add=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    role = models.CharField(max_length=50, choices=[
        ('MANAGER', 'Manager'),
        ('CASHIER', 'Cashier'),
        ('WAREHOUSE', 'Warehouse Staff'),
        ('ADMIN', 'Administrator'),
    ], default='CASHIER')

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.role})"
