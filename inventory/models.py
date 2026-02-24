from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=50, unique=True, blank=True, help_text="Stock keeping unit")
    part_number = models.CharField(max_length=50, blank=True, help_text="OEM number")
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0, help_text="Quantity at which to reorder")

    cost_price = models.FloatField(default=0)
    selling_price = models.FloatField()
    wholesale_price = models.FloatField(default=0)

    location = models.CharField(max_length=150, blank=True, help_text="Physical storage location (shelf, bin)")
    purpose = models.CharField(max_length=150, blank=True, help_text="Part purpose e.g. DIFFERENTIAL PINION")
    vehicle_application = models.TextField(blank=True, help_text="Car/vehicle types this part fits")

    compatibilities = models.ManyToManyField(
        "CarModel",
        blank=True,
        related_name="compatible_products",
        help_text="Vehicle models this part fits"
    )

    LOW_STOCK_THRESHOLD = 5

    def is_low_stock(self):
        return self.quantity <= self.LOW_STOCK_THRESHOLD

    def __str__(self):
        return self.name


class Purchase(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    total_amount = models.FloatField(default=0)

    def __str__(self):
        return f"Purchase #{self.id}"


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.FloatField()

    @property
    def line_total(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"


class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)
    year_from = models.PositiveIntegerField(null=True, blank=True)
    year_to = models.PositiveIntegerField(null=True, blank=True)
    engine_type = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ("make", "name", "year_from", "year_to")

    def __str__(self):
        parts = [self.make.name, self.name]
        if self.year_from and self.year_to:
            parts.append(f"{self.year_from}-{self.year_to}")
        return " ".join(parts)

