from django.contrib import admin
from .models import Sale, SaleItem, Customer

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email")
    search_fields = ("name", "phone", "email")

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]
    readonly_fields = ('total_amount',)
    list_display = ('id', 'date', 'customer', 'total_amount', 'payment_method')
    search_fields = ('customer__name',)

