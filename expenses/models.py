from django.db import models

class Expense(models.Model):
    CATEGORY_CHOICES = [
        ("RENT", "Rent"),
        ("SALARY", "Salary"),
        ("UTILITY", "Utility"),
        ("TRANSPORT", "Transport"),
        ("OTHER", "Other"),
    ]

    title = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.FloatField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"
