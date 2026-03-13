from django.db import models
from inventory.models import Product


class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loyalty_points = models.PositiveIntegerField(default=0, help_text="Accumulated loyalty points")

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

    def award_loyalty_points(self):
        if self.customer:
            points = int(self.calculate_total() // 10)  # 1 point per $10 spent
            if points > 0:
                self.customer.loyalty_points += points
                self.customer.save()
                LoyaltyTransaction.objects.create(
                    customer=self.customer,
                    sale=self,
                    points=points,
                    transaction_type="EARN",
                    description=f"Earned {points} points for purchase of ${self.calculate_total()}"
                )

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


class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("EARN", "Earned"),
        ("SPEND", "Spent"),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL, help_text="Sale that triggered the transaction")
    points = models.IntegerField(help_text="Points earned (positive) or spent (negative)")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.customer.name}: {self.get_transaction_type_display()} {abs(self.points)} points"
