from django.db import models
from inventory.models import Product


class Sale(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default="CASH")
    total_amount = models.FloatField(default=0)

    def calculate_total(self):
        return sum(item.quantity * item.price for item in self.items.all())

    def profit(self):
        return sum(item.profit() for item in self.items.all())

    def __str__(self):
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
