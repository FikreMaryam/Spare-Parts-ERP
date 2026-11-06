from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product


class Customer(models.Model):
    name = models.CharField(max_length=100, help_text="Buyer Contact Name or Full Name")
    company_name = models.CharField(max_length=150, blank=True, help_text="Buyer Company / Business Name")
    tin_number = models.CharField(max_length=50, blank=True, help_text="Buyer Tax Identification Number (TIN)")
    vat_number = models.CharField(max_length=50, blank=True, help_text="Buyer VAT Registration Number")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loyalty_points = models.PositiveIntegerField(default=0, help_text="Accumulated loyalty points")

    @property
    def display_name(self):
        if self.company_name and self.name:
            return f"{self.company_name} - {self.name}"
        return self.company_name or self.name or "Walk-in Customer"

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.name})"
        return self.name


class CustomerVehicle(models.Model):
    """
    Fleet & Garage vehicle registry for regular customers and workshop accounts.
    Allows one-click re-ordering of parts matched to their exact vehicle, plate, or VIN.
    """
    customer = models.ForeignKey(Customer, related_name="vehicles", on_delete=models.CASCADE)
    car_model = models.ForeignKey(
        "inventory.CarModel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_vehicles",
        help_text="Standard vehicle make and model"
    )
    custom_name = models.CharField(max_length=150, blank=True, help_text="e.g. Toyota Hilux Double Cabin 2.8L")
    plate_number = models.CharField(max_length=50, blank=True, help_text="e.g. 2-B12345 AA or 3-A67890")
    vin_number = models.CharField(max_length=50, blank=True, help_text="17-character VIN or chassis prefix")
    engine = models.CharField(max_length=80, blank=True, help_text="Engine model code e.g. 1GD-FTV, 1NZ-FE")
    manufacture_year = models.PositiveIntegerField(null=True, blank=True, help_text="e.g. 2018")
    notes = models.CharField(max_length=250, blank=True, help_text="e.g. Fleet Unit #12, Garage Assigned Driver: Tadesse")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def display_title(self):
        parts = []
        if self.plate_number:
            parts.append(f"[{self.plate_number}]")
        if self.car_model:
            parts.append(str(self.car_model))
        elif self.custom_name:
            parts.append(self.custom_name)
        else:
            parts.append("Registered Vehicle")
        if self.manufacture_year:
            parts.append(f"({self.manufacture_year})")
        return " ".join(parts)

    def __str__(self):
        return f"{self.customer.display_name} - {self.display_title}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} - {self.product.name} x {self.quantity}"


class Sale(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("TRANSFER", "Bank Transfer (CBE / Awash / Dashen)"),
        ("TELEBIRR", "Telebirr"),
        ("CBE_BIRR", "CBE Birr"),
        ("CREDIT", "Credit"),
        ("ATM", "ATM / POS Card"),
        ("CHECK", "Cheque"),
        ("OTHER", "Other"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("SHIPPED", "Shipped"),
        ("CANCELLED", "Cancelled"),
    ]

    date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
    )
    total_amount = models.FloatField(default=0)
    subtotal_amount = models.FloatField(default=0, help_text="Taxable subtotal before VAT")
    tax_amount = models.FloatField(default=0, help_text="VAT amount (15%)")
    fs_number = models.CharField(max_length=50, blank=True, help_text="Fiscal Sales (FS) Receipt Number")
    receipt_reference = models.CharField(max_length=100, blank=True, help_text="Receipt number printed on the source document")
    document_date = models.DateField(null=True, blank=True, help_text="Date printed on the source receipt")
    receipt_file = models.FileField(upload_to="sales_receipts/%Y/%m/", blank=True, null=True, help_text="Official sales receipt or supporting document")
    source_text = models.TextField(blank=True, help_text="Transcribed receipt text entered during parts analysis")
    cashier = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_recorded",
        help_text="Cashier or staff member who processed this sale"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="APPROVED")
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales",
        help_text="Shop / Store branch where sale was made"
    )
    customer = models.ForeignKey(
        "sales.Customer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Customer who made the purchase",
    )
    vehicle = models.ForeignKey(
        "sales.CustomerVehicle",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales",
        help_text="Customer vehicle this sale was made for"
    )

    def get_fs_number(self):
        if self.fs_number:
            return self.fs_number
        return f"FS-{self.id:06d}"

    @property
    def calculated_subtotal(self):
        if self.subtotal_amount > 0:
            return self.subtotal_amount
        return round(self.total_amount / 1.15, 2)

    @property
    def calculated_vat(self):
        if self.tax_amount > 0:
            return self.tax_amount
        return round(self.total_amount - self.calculated_subtotal, 2)

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


class Proforma(models.Model):
    """
    Official Proforma Invoice / Price Quotation (ፕሮፎርማ ኢንቮይስ / የዋጋ ማቅረቢያ).
    Issued to customers, businesses, and government bodies before formal sales.
    Can be converted directly into an active sale upon purchase confirmation.
    """
    STATUS_CHOICES = [
        ("DRAFT", "Draft (ረቂቅ)"),
        ("SENT", "Issued / Sent (የተሰጠ)"),
        ("CONVERTED", "Converted to Sale (ወደ ሽያጭ የተለወጠ)"),
        ("EXPIRED", "Expired (ጊዜው ያለፈበት)"),
    ]

    proforma_number = models.CharField(max_length=50, unique=True, help_text="e.g. PRF-2026-0001")
    date = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(help_text="Validity expiration date")

    # Customer & Buyer Details
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="proformas")
    buyer_name = models.CharField(max_length=150, help_text="Buyer or Contact Name")
    buyer_company = models.CharField(max_length=150, blank=True, help_text="Buyer Company Name")
    buyer_tin = models.CharField(max_length=50, blank=True, help_text="Buyer TIN Number")
    buyer_vat = models.CharField(max_length=50, blank=True, help_text="Buyer VAT Number")
    buyer_phone = models.CharField(max_length=50, blank=True)
    buyer_address = models.TextField(blank=True)

    # Store / Branch
    warehouse = models.ForeignKey(
        "inventory.Warehouse",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Issuing shop or store branch"
    )

    # Financial Summary
    total_amount = models.FloatField(default=0.0)
    subtotal_amount = models.FloatField(default=0.0, help_text="Taxable subtotal before VAT")
    tax_amount = models.FloatField(default=0.0, help_text="15% VAT amount")

    # Commercial Terms & Conditions
    payment_terms = models.CharField(max_length=200, default="100% Cash / Bank Transfer upon delivery", blank=True)
    delivery_terms = models.CharField(max_length=200, default="Ex-store Teklehaymanot, Addis Ababa", blank=True)
    notes = models.TextField(blank=True, default="All spare parts are genuine quality. Prices include 15% VAT.")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SENT")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    converted_sale = models.ForeignKey(Sale, null=True, blank=True, on_delete=models.SET_NULL, related_name="from_proforma")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        buyer = self.buyer_company or self.buyer_name or "Walk-in"
        return f"{self.proforma_number} - {buyer} ({self.total_amount:,.2f} ETB)"

    @property
    def calculated_subtotal(self):
        if self.subtotal_amount > 0:
            return self.subtotal_amount
        return round(self.total_amount / 1.15, 2)

    @property
    def calculated_vat(self):
        if self.tax_amount > 0:
            return self.tax_amount
        return round(self.total_amount - self.calculated_subtotal, 2)

    def calculate_totals(self, vat_rate_percent=15):
        tot = sum(item.quantity * item.unit_price for item in self.items.all())
        vat_rate = max(float(vat_rate_percent), 0) / 100
        sub = round(tot / (1 + vat_rate), 2) if vat_rate else round(tot, 2)
        vat = round(tot - sub, 2)
        self.total_amount = tot
        self.subtotal_amount = sub
        self.tax_amount = vat
        self.save()


class ProformaItem(models.Model):
    proforma = models.ForeignKey(Proforma, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    part_number = models.CharField(max_length=50, blank=True)
    description = models.CharField(max_length=250)
    unit = models.CharField(max_length=20, default="Pcs")
    quantity = models.FloatField(default=1.0)
    unit_price = models.FloatField(default=0.0)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.description} x {self.quantity} ({self.unit})"


class PaymentTransaction(models.Model):
    """
    Automated Mobile Money & Electronic Banking Payment Reconciliation System.
    Tracks Telebirr, CBE Birr, Awash, Dashen, and Bank transfers with reference codes.
    """
    PROVIDER_CHOICES = [
        ("TELEBIRR", "Telebirr (Ethio Telecom)"),
        ("CBE_BIRR", "CBE Birr (Commercial Bank of Ethiopia)"),
        ("CBE_TRANSFER", "CBE Mobile / Internet Banking Transfer"),
        ("AWASH_BIRR", "Awash Birr / Awash Bank"),
        ("DASHEN_AMOLE", "Dashen Bank / Amole"),
        ("BANK_OTHER", "Other Commercial Bank Transfer"),
        ("CASH", "Direct Cash"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending Verification (በማረጋገጥ ላይ)"),
        ("VERIFIED", "Verified & Settled (የተረጋገጠ)"),
        ("RECONCILED", "Reconciled to Sale (ከሽያጭ ጋር የተገናኘ)"),
        ("REJECTED", "Rejected / Invalid Reference (ውድቅ የተደረገ)"),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="TELEBIRR")
    transaction_reference = models.CharField(
        max_length=100,
        unique=True,
        help_text="SMS reference code, Telebirr Trans ID, or CBE FT number (e.g. CK79812456, FT26102...)"
    )
    amount = models.FloatField(default=0.0, help_text="Amount in ETB")
    payer_phone = models.CharField(max_length=50, blank=True, help_text="Sender phone number")
    payer_name = models.CharField(max_length=150, blank=True, help_text="Sender name from payment SMS")
    sale = models.ForeignKey(
        Sale,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payment_transactions",
        help_text="Sale invoice matched to this payment"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="VERIFIED")
    received_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_payments"
    )
    raw_sms_text = models.TextField(blank=True, help_text="Raw SMS or slip text parsed")
    notes = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.get_provider_display()}: {self.transaction_reference} - {self.amount:,.2f} ETB ({self.get_status_display()})"
