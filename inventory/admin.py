from django.contrib import admin
from .models import (
    Category,
    Product,
    Supplier,
    Purchase,
    PurchaseItem,
    CarMake,
    CarModel,
    Warehouse,
    StockMovement,
    AssemblyCategory,
    AssemblyDiagram,
    DiagramCallout,
    PartSubstitute,
)
from django.utils.safestring import mark_safe



@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact")
    search_fields = ("name",)


class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1


@admin.register(CarMake)
class CarMakeAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "location")
    search_fields = ("name", "location")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "product", "quantity", "movement_type", "warehouse")
    list_filter = ("movement_type", "warehouse")
    search_fields = ("product__name", "reference")




@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = (
        "make",
        "name",
        "year_from",
        "year_to",
        "engine_type",
        "chassis_prefixes",
    )
    search_fields = ("name", "make__name", "chassis_prefixes")
    list_filter = ("make",)


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "supplier", "invoice_number", "total_amount")
    inlines = [PurchaseItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "part_number",
        "name",
        "brand",
        "category",
        "quantity",
        "reorder_level",
        "cost_price",
        "selling_price",
        "wholesale_price",
        "location",
        "low_stock_alert",
    )
    search_fields = ("sku", "part_number", "name", "brand", "vehicle_application")
    list_filter = ("brand", "category")
    filter_horizontal = ("compatibilities",)

    def low_stock_alert(self, obj):
        if obj.quantity is not None and obj.quantity <= 5:
            return mark_safe('<span style="color:red;">LOW</span>')
        return "-"

    low_stock_alert.short_description = "Stock Alert"


@admin.register(AssemblyCategory)
class AssemblyCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon")
    search_fields = ("name",)


class DiagramCalloutInline(admin.TabularInline):
    model = DiagramCallout
    extra = 2


@admin.register(AssemblyDiagram)
class AssemblyDiagramAdmin(admin.ModelAdmin):
    list_display = ("title", "diagram_code", "car_model", "category")
    list_filter = ("category", "car_model__make")
    search_fields = ("title", "diagram_code", "car_model__name")
    inlines = [DiagramCalloutInline]


@admin.register(DiagramCallout)
class DiagramCalloutAdmin(admin.ModelAdmin):
    list_display = ("callout_number", "diagram", "product", "part_number", "x_percent", "y_percent")
    search_fields = ("callout_number", "part_number", "part_name", "product__name", "product__part_number")


@admin.register(PartSubstitute)
class PartSubstituteAdmin(admin.ModelAdmin):
    list_display = ("original_product", "substitute_product", "substitute_type")
    list_filter = ("substitute_type",)



