from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone


class BusinessProfile(models.Model):
    """
    Business information & accounting configuration for the spare parts shop.
    Supports Ethiopian business context (TIN, VAT registration, ETB currency).
    """
    name = models.CharField(max_length=200, default="Spare Parts ERP", help_text="Registered business name")
    trade_name = models.CharField(max_length=200, blank=True, default="Car Spare Parts Shop", help_text="Storefront or commercial brand name")
    tin_number = models.CharField(max_length=50, blank=True, default="0081095335", help_text="Ethiopian Tax Identification Number (TIN)")
    vat_number = models.CharField(max_length=50, blank=True, default="42178020821", help_text="Ethiopian VAT Registration Number")
    vat_registered = models.BooleanField(default=True, help_text="Is the business registered for VAT?")
    vat_rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"), help_text="Applicable VAT rate (default 15% in Ethiopia)")
    
    phone = models.CharField(max_length=50, blank=True, default="+251 911 000000")
    email = models.EmailField(blank=True, default="info@addisspares.com")
    address = models.TextField(blank=True, default="Woreda 07 Teklehaymanot, Addis Hope Building, AHG-022, Addis Ababa, Ethiopia")
    
    currency_code = models.CharField(max_length=10, default="ETB", help_text="e.g. ETB")
    currency_symbol = models.CharField(max_length=10, default="ETB", help_text="e.g. ETB or Br")
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=7, help_text="1=January (Gregorian) or 7=July (Hamle - Ethiopian fiscal year)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Profile & Accounting Settings"
        verbose_name_plural = "Business Profile & Accounting Settings"

    def __str__(self):
        return f"{self.name} ({self.currency_code})"

    @classmethod
    def get_profile(cls):
        profile = cls.objects.first()
        if not profile:
            profile = cls.objects.create(
                name="Spare Parts ERP",
                trade_name="Car Spare Parts Shop",
                tin_number="0081095335",
                vat_number="42178020821",
                address="Woreda 07 Teklehaymanot, Addis Hope Building, AHG-022, Addis Ababa, Ethiopia",
                currency_code="ETB",
                currency_symbol="ETB",
                vat_registered=True,
                vat_rate_percent=Decimal("15.00"),
            )
        elif not profile.tin_number or not profile.vat_number:
            profile.tin_number = "0081095335"
            profile.vat_number = "42178020821"
            profile.address = "Woreda 07 Teklehaymanot, Addis Hope Building, AHG-022, Addis Ababa, Ethiopia"
            profile.save()
        return profile


class VATWithholdingReceipt(models.Model):
    """Stores VAT withholding receipts issued by companies or suppliers."""
    company_name = models.CharField(max_length=200, help_text="Company or payer name")
    tin_number = models.CharField(max_length=50, blank=True, help_text="Company TIN")
    withholding_period = models.CharField(max_length=50, blank=True, help_text="Month / period / reference")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, help_text="Withheld VAT amount")
    receipt_file = models.FileField(upload_to="vat_withholding/%Y/%m/", blank=True, null=True, help_text="PDF, image, or scanned document")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "VAT Withholding Receipt"
        verbose_name_plural = "VAT Withholding Receipts"

    def __str__(self):
        return f"{self.company_name} - {self.amount} ETB"


class OpeningBalance(models.Model):
    """
    Opening baseline balance sheet amounts for a specific financial period.
    Ensures Balance Sheet and Cash Flow reports are anchored to real audited baselines.
    """
    effective_date = models.DateField(default=timezone.now, help_text="Effective start date for this financial baseline")
    
    # Current Assets
    opening_cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Cash on hand in till / safe")
    opening_bank = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Commercial bank accounts (e.g. CBE, Dashen, Awash)")
    opening_mobile_money = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Mobile money balances (e.g. Telebirr, CBE Birr)")
    opening_inventory_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Valuation of inventory stock on hand at period start")
    opening_receivables = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Outstanding customer credit debt owed to the shop")
    
    # Non-Current Assets
    opening_equipment_assets = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Shop fixtures, shelves, diagnostic tools, vehicles")
    
    # Liabilities
    opening_payables = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Outstanding supplier bills owed by the shop")
    opening_loans_liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Bank loans, credit lines or other liabilities")
    
    # Equity
    owner_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Owner initial invested capital")
    retained_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Accumulated undistributed profits from prior periods")

    notes = models.TextField(blank=True, help_text="Audit notes, source documents, or accountant confirmation")
    is_locked = models.BooleanField(default=False, help_text="Lock to prevent accidental modification once audited")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]
        verbose_name = "Opening Balance Baseline"
        verbose_name_plural = "Opening Balance Baselines"

    def __str__(self):
        return f"Opening Balance as of {self.effective_date} (Inv: {self.opening_inventory_value} ETB)"

    @property
    def total_assets(self):
        return (
            self.opening_cash +
            self.opening_bank +
            self.opening_mobile_money +
            self.opening_inventory_value +
            self.opening_receivables +
            self.opening_equipment_assets
        )

    @property
    def total_liabilities_and_equity(self):
        return (
            self.opening_payables +
            self.opening_loans_liabilities +
            self.owner_capital +
            self.retained_earnings
        )


class CustomerPayment(models.Model):
    """
    Payments received from customers towards credit sales or account balances.
    Tracks cash inflows and updates customer receivables.
    """
    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("BANK_TRANSFER", "Bank Transfer (CBE / Awash / Dashen)"),
        ("TELEBIRR", "Telebirr"),
        ("CBE_BIRR", "CBE Birr"),
        ("CHECK", "Cheque"),
        ("OTHER", "Other"),
    ]

    customer = models.ForeignKey("sales.Customer", on_delete=models.CASCADE, related_name="payments")
    sale = models.ForeignKey("sales.Sale", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments", help_text="Optional link to a specific credit invoice")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default="CASH")
    reference = models.CharField(max_length=100, blank=True, help_text="Bank slip #, Telebirr txn ID, or receipt #")
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        verbose_name = "Customer Payment"
        verbose_name_plural = "Customer Payments"

    def __str__(self):
        return f"Payment #{self.id}: {self.customer.name} - {self.amount} ETB ({self.payment_date})"


class SupplierPayment(models.Model):
    """
    Payments made by the shop to suppliers towards purchase invoices.
    Tracks cash outflows and reduces supplier payables.
    """
    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("BANK_TRANSFER", "Bank Transfer"),
        ("TELEBIRR", "Telebirr"),
        ("CHECK", "Cheque"),
        ("OTHER", "Other"),
    ]

    supplier = models.ForeignKey("inventory.Supplier", on_delete=models.CASCADE, related_name="payments")
    purchase = models.ForeignKey("inventory.Purchase", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments", help_text="Optional link to a specific PO/invoice")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default="CASH")
    reference = models.CharField(max_length=100, blank=True, help_text="Bank transfer slip #, check #, or receipt #")
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date", "-id"]
        verbose_name = "Supplier Payment"
        verbose_name_plural = "Supplier Payments"

    def __str__(self):
        return f"Supplier Payment #{self.id}: {self.supplier.name} - {self.amount} ETB ({self.payment_date})"


class StockCountAdjustment(models.Model):
    """
    Physical stock-take adjustment record with audit trail, user accountability, and reason.
    Reconciles physical shelf stock with database quantity.
    """
    REASON_CHOICES = [
        ("COUNT_CORRECTION", "Physical Count Discrepancy / Recount"),
        ("DAMAGED", "Damaged in Shop / Defective Item"),
        ("THEFT_LOSS", "Theft or Unaccounted Loss"),
        ("OBSOLETE", "Obsolete / Scrap Item"),
        ("SUPPLIER_SAMPLE", "Supplier Demo / Testing"),
        ("OTHER", "Other Reason"),
    ]

    product = models.ForeignKey("inventory.Product", on_delete=models.CASCADE, related_name="stock_counts")
    counted_date = models.DateField(default=timezone.now)
    system_quantity = models.IntegerField(help_text="Stock quantity recorded in ERP before count")
    physical_quantity = models.IntegerField(help_text="Actual physical units counted on shelf/bin")
    difference = models.IntegerField(help_text="Difference (Physical - System)")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Unit cost at time of adjustment")
    financial_impact = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), help_text="Cost impact (diff * unit_cost)")
    
    reason = models.CharField(max_length=40, choices=REASON_CHOICES, default="COUNT_CORRECTION")
    notes = models.TextField(blank=True, help_text="Detailed explanation of reason for audit trail")
    audited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-counted_date", "-id"]
        verbose_name = "Physical Stock Adjustment"
        verbose_name_plural = "Physical Stock Adjustments"

    def __str__(self):
        diff_str = f"+{self.difference}" if self.difference > 0 else str(self.difference)
        return f"Stock Count: {self.product.name} ({diff_str} units) on {self.counted_date}"
