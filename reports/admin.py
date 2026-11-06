from django.contrib import admin
from .models import BusinessProfile, OpeningBalance, CustomerPayment, SupplierPayment, StockCountAdjustment


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "trade_name", "tin_number", "vat_registered", "vat_rate_percent", "currency_code")


@admin.register(OpeningBalance)
class OpeningBalanceAdmin(admin.ModelAdmin):
    list_display = ("effective_date", "opening_cash", "opening_bank", "opening_inventory_value", "opening_receivables", "opening_payables", "is_locked")
    list_filter = ("is_locked", "effective_date")


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "amount", "payment_date", "payment_method", "reference")
    list_filter = ("payment_method", "payment_date")
    search_fields = ("customer__name", "reference", "notes")


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "amount", "payment_date", "payment_method", "reference")
    list_filter = ("payment_method", "payment_date")
    search_fields = ("supplier__name", "reference", "notes")


@admin.register(StockCountAdjustment)
class StockCountAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("product", "counted_date", "system_quantity", "physical_quantity", "difference", "financial_impact", "reason")
    list_filter = ("reason", "counted_date")
    search_fields = ("product__name", "product__part_number", "notes")
