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
    warehouse = models.ForeignKey(
        "Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Where the goods are received",
    )
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


class Warehouse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StockMovement(models.Model):
    MOVEMENT_CHOICES = [
        ("purchase", "Purchase"),
        ("sale", "Sale"),
        ("adjustment", "Adjustment"),
        ("transfer", "Transfer"),
    ]
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Warehouse where the movement occurred",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} x {self.product.name}"


class Account(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    class Meta:
        verbose_name_plural = "accounts"

    def __str__(self):
        if self.code:
            return f"{self.code} - {self.name}"
        return self.name


class JournalEntry(models.Model):
    date = models.DateField()
    description = models.TextField(blank=True)
    debit_account = models.ForeignKey(
        Account, related_name="debits", on_delete=models.CASCADE
    )
    credit_account = models.ForeignKey(
        Account, related_name="credits", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.date} {self.amount}: {self.description[:30]}"


class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)
    year_from = models.PositiveIntegerField(null=True, blank=True)
    year_to = models.PositiveIntegerField(null=True, blank=True)
    engine_type = models.CharField(max_length=100, blank=True)
    # vehicle chassis codes or prefixes – comma separated list
    chassis_prefixes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated chassis codes or prefixes used for quick lookup",
    )

    class Meta:
        unique_together = ("make", "name", "year_from", "year_to")

    def __str__(self):
        parts = [self.make.name, self.name]
        if self.year_from and self.year_to:
            parts.append(f"{self.year_from}-{self.year_to}")
        return " ".join(parts)

    def matches_chassis(self, chassis_number: str) -> bool:
        """Return ``True`` if the given chassis number matches any of the
        prefixes configured on this model.

        The field ``chassis_prefixes`` stores a comma-separated list of codes
        or prefixes.  A match occurs when one of the prefixes is contained at
        the start of the provided chassis number (case‑insensitive).  This
        keeps the lookup simple while still allowing users to paste an entire
        chassis/VIN and get the correct car type back.
        """
        if not chassis_number:
            return False
        value = chassis_number.strip().lower()
        for prefix in (self.chassis_prefixes or "").split(","):
            pref = prefix.strip().lower()
            if pref and value.startswith(pref):
                return True
        return False

