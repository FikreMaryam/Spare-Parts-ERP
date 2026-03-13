from django.db import models
from inventory.models import Product


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("CREDIT", "Credit"),
        ("ATM", "ATM"),
        ("TRANSFER", "Bank Transfer"),
        ("MOBILE", "Mobile Payment"),
        ("OTHER", "Other"),
    ]

    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
    )
    total_amount = models.FloatField(default=0)
    customer = models.ForeignKey(
        "sales.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Customer who made the purchase",
    )

    def calculate_total(self):
        return sum(item.quantity * item.price for item in self.items.all())

    def profit(self):
        return sum(item.profit() for item in self.items.all())

    def __str__(self):
        if self.customer:
            return f"Sale #{self.id} ({self.customer.name})"
        return f"Sale #{self.id}"


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        related_name="items",
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.FloatField()
    cost_price = models.FloatField(default=0)  # IMPORTANT: default added

    def profit(self):
        return (self.price - self.cost_price) * self.quantity

    @property
    def line_total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"
