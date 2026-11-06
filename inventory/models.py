from django.conf import settings
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
    UOM_CHOICES = [
        ("PCS", "Pieces (Pcs / ቁራጭ)"),
        ("LTR", "Litre (L / ሊትር)"),
        ("KG", "Kilogram (Kg / ኪ.ግ)"),
        ("SET", "Set (Set / ስብስብ)"),
        ("MTR", "Metre (M / ሜትር)"),
        ("CAN", "Can / Tin (ቆርቆሮ)"),
        ("BTL", "Bottle (ጠርሙስ)"),
        ("ROL", "Roll (ጥቅል)"),
        ("BOX", "Box (ካርቶን)"),
    ]

    sku = models.CharField(max_length=50, unique=True, blank=True, help_text="Stock keeping unit")
    part_number = models.CharField(max_length=50, blank=True, help_text="OEM number")
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    unit_of_measure = models.CharField(
        max_length=10,
        choices=UOM_CHOICES,
        default="PCS",
        help_text="Unit of measurement (e.g. Pcs, Litre, Kg, Set)"
    )
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0, help_text="Quantity at which to reorder")

    cost_price = models.FloatField(default=0)
    selling_price = models.FloatField()
    wholesale_price = models.FloatField(default=0)

    location = models.CharField(max_length=150, blank=True, help_text="Physical storage location (shelf, bin)")
    purpose = models.CharField(max_length=150, blank=True, help_text="Part purpose e.g. DIFFERENTIAL PINION")
    vehicle_application = models.TextField(blank=True, help_text="Car/vehicle types this part fits")
    image = models.ImageField(upload_to="products/", blank=True, null=True, help_text="Product photo")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    compatibilities = models.ManyToManyField(
        "CarModel",
        blank=True,
        related_name="compatible_products",
        help_text="Vehicle models this part fits"
    )

    alternate_numbers = models.CharField(max_length=255, blank=True, help_text="Comma-separated cross-reference or alternate part numbers")
    shelf_bin = models.CharField(max_length=50, blank=True, help_text="Shelf/Bin storage code e.g. A-12-3")
    is_genuine = models.BooleanField(default=True, help_text="Is this a Genuine OEM part?")
    manufacturer_brand = models.CharField(max_length=100, blank=True, help_text="Manufacturer brand name e.g. Toyota OEM, Denso, Bosch")

    LOW_STOCK_THRESHOLD = 5

    def is_low_stock(self):
        return self.quantity <= self.LOW_STOCK_THRESHOLD

    @property
    def uom_short(self):
        mapping = {
            "PCS": "Pcs",
            "LTR": "Ltr",
            "KG": "Kg",
            "SET": "Set",
            "MTR": "Mtr",
            "CAN": "Can",
            "BTL": "Btl",
            "ROL": "Rol",
            "BOX": "Box",
        }
        return mapping.get(self.unit_of_measure, self.unit_of_measure)

    @property
    def uom_amharic(self):
        mapping = {
            "PCS": "ቁራጭ",
            "LTR": "ሊትር",
            "KG": "ኪ.ግ",
            "SET": "ስብስብ",
            "MTR": "ሜትር",
            "CAN": "ቆርቆሮ",
            "BTL": "ጠርሙስ",
            "ROL": "ጥቅል",
            "BOX": "ካርቶን",
        }
        return mapping.get(self.unit_of_measure, "ቁራጭ")

    def __str__(self):
        if self.part_number:
            return f"[{self.part_number}] {self.name}"
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
    document_date = models.DateField(null=True, blank=True, help_text="Date printed on the supplier receipt")
    notes = models.CharField(max_length=200, blank=True)
    receipt_file = models.FileField(upload_to="purchase_receipts/%Y/%m/", blank=True, null=True, help_text="Purchase invoice or supplier receipt upload")
    source_text = models.TextField(blank=True, help_text="Transcribed receipt text entered during parts analysis")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="recorded_purchases",
    )
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
    BRANCH_TYPES = [
        ("RETAIL_SHOP", "Retail Shop / Storefront (መደብር)"),
        ("WAREHOUSE", "Central Warehouse / Store (መጋዘን)"),
        ("DEPOT", "Transit Depot / Workshop (ዲፖ)"),
    ]
    name = models.CharField(max_length=100, unique=True, help_text="e.g. Teklehaymanot Main Shop, Addis Hope Store AHG-022, Bole Branch")
    code = models.CharField(max_length=20, blank=True, help_text="Short identifier e.g. SH-01, WH-01")
    branch_type = models.CharField(max_length=20, choices=BRANCH_TYPES, default="RETAIL_SHOP")
    location = models.CharField(max_length=150, blank=True, help_text="City, Sub-city, Woreda, Building")
    phone = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def total_products_count(self):
        return self.product_stocks.filter(quantity__gt=0).count()

    def total_stock_value(self):
        return sum(item.quantity * item.product.cost_price for item in self.product_stocks.select_related('product'))

    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.name}"
        return self.name


class ProductBranchStock(models.Model):
    """
    Tracks inventory quantities for each spare part across multiple shops and warehouses.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="branch_stocks")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="product_stocks")
    quantity = models.FloatField(default=0, help_text="Quantity available at this specific shop/store")
    shelf_bin = models.CharField(max_length=50, blank=True, help_text="Specific shelf/bin in this shop/store")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product", "warehouse")
        verbose_name = "Shop & Warehouse Stock"
        verbose_name_plural = "Shop & Warehouse Stocks"

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity} {self.product.uom_short}"


class ImportShipment(models.Model):
    """
    Materials & Spare Parts Import Tracking and Landed Cost Calculation System.
    Apportions foreign currency FOB costs, freight, insurance, Ethiopian customs tariffs,
    and port clearance to calculate true landed cost per unit in ETB.
    """
    STATUS_CHOICES = [
        ("PLANNED", "Planned / Order Placed"),
        ("TRANSIT", "In Transit (Sea/Air Freight)"),
        ("CUSTOMS", "At Customs / Port Clearance"),
        ("ARRIVED", "Arrived & Received in Warehouse"),
        ("CANCELLED", "Cancelled"),
    ]
    CURRENCY_CHOICES = [
        ("USD", "USD ($)"),
        ("EUR", "EUR (€)"),
        ("AED", "AED (UAE Dirham)"),
        ("CNY", "CNY (Chinese Yuan RMB)"),
        ("ETB", "ETB (Ethiopian Birr)"),
    ]

    shipment_number = models.CharField(max_length=50, unique=True, help_text="e.g. IMP-2026-001")
    title = models.CharField(max_length=150, blank=True, help_text="e.g. Toyota Suspension & Brake Parts Container")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    destination_warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, help_text="Receiving shop or warehouse")
    origin_country = models.CharField(max_length=100, blank=True, default="China", help_text="e.g. China, Dubai, Turkey, Japan, Germany")
    departure_port = models.CharField(max_length=100, blank=True, help_text="e.g. Ningbo, Guangzhou, Jebel Ali")
    arrival_port = models.CharField(max_length=100, blank=True, default="Modjo Dry Port / Addis Ababa", help_text="e.g. Djibouti / Modjo Dry Port / Kality")

    # Currency & Foreign Exchange
    currency = models.CharField(max_length=10, default="USD", choices=CURRENCY_CHOICES)
    exchange_rate = models.FloatField(default=135.0, help_text="Exchange rate to ETB at time of customs clearance (e.g. 1 USD = 135 ETB)")

    # Direct Landed Costs Breakdown (in ETB)
    freight_cost_etb = models.FloatField(default=0.0, help_text="International Sea/Air Shipping & Freight (ETB)")
    insurance_cost_etb = models.FloatField(default=0.0, help_text="Marine / Cargo Insurance (ETB)")
    customs_duty_etb = models.FloatField(default=0.0, help_text="Ethiopian Customs Duty, Sur-tax, Withholding (ETB)")
    port_handling_etb = models.FloatField(default=0.0, help_text="Djibouti port handling, transit, clearing agent fees (ETB)")
    inland_transport_etb = models.FloatField(default=0.0, help_text="Trucking from Djibouti / Modjo to Shop (ETB)")
    other_clearing_costs_etb = models.FloatField(default=0.0, help_text="Bank LC fees, warehouse storage, miscellaneous (ETB)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PLANNED")
    order_date = models.DateField(auto_now_add=True)
    expected_arrival_date = models.DateField(null=True, blank=True)
    actual_arrival_date = models.DateField(null=True, blank=True)
    bill_of_lading = models.CharField(max_length=100, blank=True, help_text="B/L or Airway Bill Number")
    notes = models.TextField(blank=True)

    def total_direct_landed_costs_etb(self):
        return (
            self.freight_cost_etb
            + self.insurance_cost_etb
            + self.customs_duty_etb
            + self.port_handling_etb
            + self.inland_transport_etb
            + self.other_clearing_costs_etb
        )

    def total_fob_foreign_currency(self):
        return sum(item.foreign_fob_price * item.quantity for item in self.items.all())

    def total_fob_etb(self):
        return self.total_fob_foreign_currency() * self.exchange_rate

    def total_shipment_landed_cost_etb(self):
        return self.total_fob_etb() + self.total_direct_landed_costs_etb()

    def recalculate_landed_costs(self):
        """
        Apportions all landing overhead expenses (freight, duty, clearance)
        proportionally by item value to compute the true landed cost per part in ETB.
        """
        items = list(self.items.all())
        total_fob_etb = self.total_fob_etb()
        total_overhead_etb = self.total_direct_landed_costs_etb()

        for item in items:
            item_fob_etb = item.foreign_fob_price * self.exchange_rate
            item_total_fob_etb = item_fob_etb * item.quantity
            
            # Apportion overhead proportionally by FOB value
            if total_fob_etb > 0:
                share = item_total_fob_etb / total_fob_etb
                allocated_total = share * total_overhead_etb
                allocated_per_unit = allocated_total / item.quantity if item.quantity > 0 else 0
            else:
                allocated_per_unit = 0

            item.allocated_overhead_per_unit_etb = round(allocated_per_unit, 2)
            item.calculated_landed_cost_per_unit_etb = round(item_fob_etb + allocated_per_unit, 2)
            
            # Default target selling price: 25% gross margin
            if not item.target_selling_price_etb:
                item.target_selling_price_etb = round(item.calculated_landed_cost_per_unit_etb * 1.30, 2)
            item.save()

    def apply_to_inventory(self):
        """
        Transfers imported parts into warehouse inventory and updates product cost price.
        """
        self.recalculate_landed_costs()
        for item in self.items.all():
            prod = item.product
            # Weighted average cost or latest landed cost
            prod.cost_price = item.calculated_landed_cost_per_unit_etb
            if item.target_selling_price_etb > 0:
                prod.selling_price = item.target_selling_price_etb
            prod.quantity += int(item.quantity)
            prod.save()

            # Record branch stock if warehouse is selected
            if self.destination_warehouse:
                bs, _ = ProductBranchStock.objects.get_or_create(
                    product=prod,
                    warehouse=self.destination_warehouse,
                    defaults={'quantity': 0}
                )
                bs.quantity += item.quantity
                bs.save()

            StockMovement.objects.create(
                product=prod,
                quantity=int(item.quantity),
                movement_type="purchase",
                reference=f"Import #{self.shipment_number}",
                warehouse=self.destination_warehouse,
            )
        self.status = "ARRIVED"
        self.save()

    def __str__(self):
        return f"{self.shipment_number} - {self.title or self.origin_country} ({self.total_shipment_landed_cost_etb():,.2f} ETB)"


class ImportShipmentItem(models.Model):
    shipment = models.ForeignKey(ImportShipment, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.FloatField(default=1.0)
    foreign_fob_price = models.FloatField(help_text="Unit purchase price in foreign currency (e.g. USD)")
    customs_tariff_code = models.CharField(max_length=50, blank=True, help_text="Harmonized System (HS) Code e.g. 8708.29")

    # Calculated landed cost values
    allocated_overhead_per_unit_etb = models.FloatField(default=0.0)
    calculated_landed_cost_per_unit_etb = models.FloatField(default=0.0)
    target_selling_price_etb = models.FloatField(default=0.0)

    @property
    def total_fob_foreign(self):
        return self.quantity * self.foreign_fob_price

    @property
    def total_landed_cost_etb(self):
        return self.quantity * self.calculated_landed_cost_per_unit_etb

    def __str__(self):
        return f"{self.product.name} x {self.quantity} (Landed: {self.calculated_landed_cost_per_unit_etb:,.2f} ETB)"


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


class AssemblyCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    icon = models.CharField(max_length=50, default="fa-cogs", help_text="FontAwesome or SVG icon name")
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Assembly Categories"

    def __str__(self):
        return self.name


class AssemblyDiagram(models.Model):
    car_model = models.ForeignKey(CarModel, on_delete=models.CASCADE, related_name="diagrams")
    category = models.ForeignKey(AssemblyCategory, on_delete=models.CASCADE, related_name="diagrams")
    title = models.CharField(max_length=150, help_text="Diagram title e.g. CYLINDER BLOCK & OIL PAN")
    diagram_code = models.CharField(max_length=50, blank=True, help_text="Schematic code e.g. 11-01")
    image = models.ImageField(upload_to="diagrams/", blank=True, null=True)
    svg_data = models.TextField(blank=True, help_text="Inline SVG schematic markup if available")
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.car_model} - {self.title} ({self.diagram_code})"


class DiagramCallout(models.Model):
    diagram = models.ForeignKey(AssemblyDiagram, on_delete=models.CASCADE, related_name="callouts")
    callout_number = models.CharField(max_length=50, help_text="Callout key e.g. 1, 2, or part callout 45100A")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="callouts")
    part_name = models.CharField(max_length=150, blank=True, help_text="Part title if product not linked")
    part_number = models.CharField(max_length=50, blank=True, help_text="OEM number if product not linked")
    x_percent = models.FloatField(default=50.0, help_text="X position percentage on image (0-100)")
    y_percent = models.FloatField(default=50.0, help_text="Y position percentage on image (0-100)")
    width_percent = models.FloatField(default=6.0, help_text="Width percentage")
    height_percent = models.FloatField(default=4.0, help_text="Height percentage")
    required_qty = models.PositiveIntegerField(default=1, help_text="Quantity required per vehicle")
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        part_str = self.product.part_number if self.product else (self.part_number or self.part_name)
        return f"[{self.callout_number}] {part_str} on {self.diagram.title}"


class PartSubstitute(models.Model):
    SUBSTITUTE_TYPES = [
        ("OEM", "Genuine OEM Equivalent"),
        ("AFTERMARKET", "Aftermarket Brand"),
        ("PERFORMANCE", "Performance Upgrade"),
    ]
    original_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="substitutes")
    substitute_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="substitute_for")
    substitute_type = models.CharField(max_length=20, choices=SUBSTITUTE_TYPES, default="AFTERMARKET")
    notes = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.substitute_product.name} substitute for {self.original_product.name}"
