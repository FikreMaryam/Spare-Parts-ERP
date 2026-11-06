from django.contrib import admin
from .models import Sale, SaleItem, Customer, CustomerVehicle, PaymentTransaction, Proforma, ProformaItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

class ProformaItemInline(admin.TabularInline):
    model = ProformaItem
    extra = 1

class CustomerVehicleInline(admin.TabularInline):
    model = CustomerVehicle
    extra = 1

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "company_name", "tin_number", "phone", "loyalty_points")
    search_fields = ("name", "company_name", "tin_number", "phone", "email")
    inlines = [CustomerVehicleInline]

@admin.register(CustomerVehicle)
class CustomerVehicleAdmin(admin.ModelAdmin):
    list_display = ("plate_number", "customer", "car_model", "custom_name", "vin_number", "manufacture_year")
    search_fields = ("plate_number", "vin_number", "custom_name", "customer__name")
    list_filter = ("car_model__make",)

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_reference", "provider", "amount", "payer_name", "payer_phone", "status", "sale", "received_at")
    list_filter = ("provider", "status", "received_at")
    search_fields = ("transaction_reference", "payer_phone", "payer_name")

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    readonly_fields = ('total_amount',)
    list_display = ('id', 'fs_number', 'date', 'customer', 'vehicle', 'total_amount', 'payment_method', 'status')
    search_fields = ('customer__name', 'fs_number')

@admin.register(Proforma)
class ProformaAdmin(admin.ModelAdmin):
    inlines = [ProformaItemInline]
    list_display = ('proforma_number', 'buyer_name', 'buyer_company', 'date', 'valid_until', 'total_amount', 'status')
    search_fields = ('proforma_number', 'buyer_name', 'buyer_company', 'buyer_tin')


