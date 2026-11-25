from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Case, F, IntegerField, Q, Sum, Value, When
from django.core.paginator import Paginator
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .forms import ProductForm
from .models import Product, Category, Purchase, PurchaseItem, Supplier, Warehouse, CarMake, CarModel
from .fitment import verify_product_fitment
from .cross_reference import get_product_cross_references, parse_alternate_numbers


SORT_FIELDS = {
    "name": "name",
    "part": "part_number",
    "brand": "brand",
    "category": "category__name",
    "qty": "quantity",
    "price": "selling_price",
    "cost": "cost_price",
}


@login_required
def product_list(request):
    products = Product.objects.select_related("category").prefetch_related("compatibilities__make")

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(sku__icontains=q)
            | Q(part_number__icontains=q)
            | Q(brand__icontains=q)
            | Q(location__icontains=q)
            | Q(vehicle_application__icontains=q)
            | Q(purpose__icontains=q)
            | Q(compatibilities__name__icontains=q)
            | Q(compatibilities__make__name__icontains=q)
            | Q(compatibilities__chassis_prefixes__icontains=q)
        ).distinct()

    # Vehicle fitment filters
    car_make_id = request.GET.get("make", "").strip()
    car_model_id = request.GET.get("carmodel", "").strip()
    active_make = None
    active_model = None

    if car_model_id:
        try:
            active_model = CarModel.objects.select_related("make").get(id=car_model_id)
            products = products.filter(compatibilities=active_model).distinct()
            car_make_id = str(active_model.make_id)
            active_make = active_model.make
        except CarModel.DoesNotExist:
            car_model_id = ""

    if car_make_id and not active_model:
        try:
            active_make = CarMake.objects.get(id=car_make_id)
            products = products.filter(compatibilities__make=active_make).distinct()
        except CarMake.DoesNotExist:
            car_make_id = ""

    # Filters
    category_id = request.GET.get("category", "")
    if category_id:
        products = products.filter(category_id=category_id)

    brand_filter = request.GET.get("brand", "").strip()
    if brand_filter:
        products = products.filter(brand__iexact=brand_filter)

    stock_filter = request.GET.get("stock", "")
    if stock_filter == "low":
        products = products.filter(
            Q(reorder_level__gt=0, quantity__lte=F("reorder_level"))
            | Q(reorder_level=0, quantity__lte=Product.LOW_STOCK_THRESHOLD)
        )
    elif stock_filter == "ok":
        products = products.filter(
            Q(reorder_level__gt=0, quantity__gt=F("reorder_level"))
            | Q(reorder_level=0, quantity__gt=Product.LOW_STOCK_THRESHOLD)
        )
    elif stock_filter == "out":
        products = products.filter(quantity=0)

    # Show filters (New arrivals, top items)
    show = request.GET.get("show", "")
    if show == "new":
        products = products.order_by("-created_at", "-id")
    elif show == "top":
        products = products.annotate(total_sold=Sum("saleitem__quantity")).order_by("-total_sold", "name")
    else:
        # Sorting
        sort = request.GET.get("sort", "name")
        order = request.GET.get("order", "asc")
        if sort in SORT_FIELDS and order in ("asc", "desc"):
            field = SORT_FIELDS[sort]
            products = products.order_by(("-" if order == "desc" else "") + field)

    # Pagination
    per_page = min(int(request.GET.get("per_page", 25) or 25), 100)
    per_page = max(per_page, 10)
    paginator = Paginator(products, per_page)
    page_num = request.GET.get("page", 1)
    page = paginator.get_page(page_num)

    # Filter options for dropdowns
    categories = Category.objects.all().order_by("name")
    brands = (
        Product.objects.exclude(brand="")
        .exclude(brand__isnull=True)
        .values_list("brand", flat=True)
        .distinct()
        .order_by("brand")
    )
    car_makes = CarMake.objects.prefetch_related("models").order_by("name")

    return render(request, "inventory/product_list.html", {
        "products": page,
        "page": page,
        "categories": categories,
        "brands": brands,
        "car_makes": car_makes,
        "search": q,
        "sort": sort,
        "order": order,
        "filter_category": category_id,
        "filter_brand": brand_filter,
        "filter_stock": stock_filter,
        "filter_make": car_make_id,
        "filter_model": car_model_id,
        "active_make": active_make,
        "active_model": active_model,
        "per_page": per_page,
    })


@login_required
def reorder_suggestions(request):
    """List products at or below their reorder point with a suggested top-up quantity."""
    low_stock_filter = (
        Q(reorder_level__gt=0, quantity__lte=F("reorder_level"))
        | Q(reorder_level=0, quantity__lte=Product.LOW_STOCK_THRESHOLD)
    )
    products = (
        Product.objects.select_related("category")
        .filter(low_stock_filter)
        .annotate(
            reorder_target=Case(
                When(reorder_level__gt=0, then=F("reorder_level")),
                default=Value(Product.LOW_STOCK_THRESHOLD),
                output_field=IntegerField(),
            )
        )
        .annotate(suggested_order_quantity=F("reorder_target") - F("quantity"))
        .order_by("quantity", "name")
    )
    page = Paginator(products, 50).get_page(request.GET.get("page"))
    return render(request, "inventory/reorder_suggestions.html", {
        "products": page,
        "page": page,
        "total_products": page.paginator.count,
    })


@login_required
def product_detail(request, pk):
    """Show detailed information for a single product with fitment verification and cross-reference."""
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("compatibilities__make", "substitutes__substitute_product"),
        pk=pk
    )

    vin = request.GET.get("vin", "").strip()
    carmodel_id = request.GET.get("carmodel", "").strip()
    target_model_id = int(carmodel_id) if carmodel_id.isdigit() else None

    # Check fitment
    fitment_result = verify_product_fitment(
        product,
        vin_or_query=vin,
        car_model_id=target_model_id
    )

    # Get complete cross-reference information
    cross_refs = get_product_cross_references(product)
    car_makes = CarMake.objects.prefetch_related("models").order_by("name")

    return render(request, "inventory/product_detail.html", {
        "product": product,
        "fitment_result": fitment_result,
        "cross_refs": cross_refs,
        "vin_query": vin,
        "carmodel_id": target_model_id,
        "car_makes": car_makes,
    })


@login_required
def verify_fitment_api(request):
    """
    JSON API endpoint for instant client-side vehicle fitment verification.
    Accepts GET or POST: product_id, vin, car_model_id.
    """
    prod_id = request.GET.get("product_id") or request.POST.get("product_id")
    vin = (request.GET.get("vin") or request.POST.get("vin") or "").strip()
    carmodel_id = (request.GET.get("car_model_id") or request.POST.get("car_model_id") or "").strip()

    if not prod_id:
        return JsonResponse({"success": False, "error": "Missing product_id"}, status=400)

    try:
        product = Product.objects.prefetch_related("compatibilities__make", "substitutes__substitute_product").get(id=prod_id)
    except Product.DoesNotExist:
        return JsonResponse({"success": False, "error": "Product not found"}, status=404)

    target_model_id = int(carmodel_id) if carmodel_id.isdigit() else None
    result = verify_product_fitment(product, vin_or_query=vin, car_model_id=target_model_id)

    return JsonResponse({
        "success": True,
        "product_id": product.id,
        "part_number": product.part_number,
        "product_name": product.name,
        "fits": result.get("fits"),
        "status": result.get("status"),
        "badge_class": result.get("badge_class"),
        "badge_text": result.get("badge_text"),
        "matched_vehicle": result.get("matched_vehicle"),
        "detail": result.get("detail"),
        "icon": result.get("icon"),
    })


@login_required
def export_inventory(request):
    """Export the editable product fields and the lookup lists used by product forms."""
    products = Product.objects.select_related("category").prefetch_related("compatibilities__make")

    # Apply same filters as product_list for consistency
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(sku__icontains=q)
            | Q(part_number__icontains=q)
            | Q(brand__icontains=q)
            | Q(location__icontains=q)
            | Q(vehicle_application__icontains=q)
            | Q(purpose__icontains=q)
            | Q(compatibilities__name__icontains=q)
            | Q(compatibilities__make__name__icontains=q)
            | Q(compatibilities__chassis_prefixes__icontains=q)
        ).distinct()

    car_make_id = request.GET.get("make", "").strip()
    car_model_id = request.GET.get("carmodel", "").strip()
    if car_model_id:
        products = products.filter(compatibilities__id=car_model_id).distinct()
    elif car_make_id:
        products = products.filter(compatibilities__make_id=car_make_id).distinct()

    category_id = request.GET.get("category", "")
    if category_id:
        products = products.filter(category_id=category_id)
    brand_filter = request.GET.get("brand", "").strip()
    if brand_filter:
        products = products.filter(brand__iexact=brand_filter)
    stock_filter = request.GET.get("stock", "")
    if stock_filter == "low":
        products = products.filter(
            Q(reorder_level__gt=0, quantity__lte=F("reorder_level"))
            | Q(reorder_level=0, quantity__lte=Product.LOW_STOCK_THRESHOLD)
        )
    elif stock_filter == "ok":
        products = products.filter(
            Q(reorder_level__gt=0, quantity__gt=F("reorder_level"))
            | Q(reorder_level=0, quantity__gt=Product.LOW_STOCK_THRESHOLD)
        )

    products = products.order_by("name")

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory"

    headers = [
        "Part Number",
        "SKU",
        "Product Name",
        "Brand",
        "Manufacturer / Origin",
        "Genuine OEM",
        "Category",
        "Unit of Measure",
        "Cost Price",
        "Selling Price",
        "Wholesale Price",
        "Stock Quantity",
        "Minimum Stock",
        "Storage Location",
        "Shelf / Bin",
        "Purpose",
        "Vehicle Application",
        "Alternate Part Numbers",
        "Car Brand",
        "Car Model",
    ]
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    for row, product in enumerate(products, 2):
        compatible_models = sorted(
            product.compatibilities.select_related("make").all(),
            key=lambda model: (model.make.name.casefold(), model.name.casefold()),
        )
        car_brands = [model.make.name for model in compatible_models]
        car_models = [str(model) for model in compatible_models]

        values = [
            product.part_number or "",
            product.sku or "",
            product.name,
            product.brand or "",
            product.manufacturer_brand or "",
            product.is_genuine,
            product.category.name if product.category else "",
            product.unit_of_measure,
            float(product.cost_price),
            float(product.selling_price),
            float(product.wholesale_price),
            product.quantity,
            product.reorder_level,
            product.location or "",
            product.shelf_bin or "",
            product.purpose or "",
            product.vehicle_application or "",
            product.alternate_numbers or "",
            " | ".join(car_brands),
            " | ".join(car_models),
        ]
        for col, value in enumerate(values, 1):
            ws.cell(row=row, column=col, value=value)

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 18
    ws.column_dimensions["C"].width = 32
    ws.column_dimensions["E"].width = 24
    ws.column_dimensions["Q"].width = 32
    ws.auto_filter.ref = ws.dimensions

    categories_ws = wb.create_sheet("Categories")
    categories_ws.append(["Category"])
    for category in Category.objects.order_by("name"):
        categories_ws.append([category.name])

    brands_ws = wb.create_sheet("Brands")
    brands_ws.append(["Brand"])
    for brand in Product.objects.exclude(brand="").exclude(brand__isnull=True).values_list("brand", flat=True).distinct().order_by("brand"):
        brands_ws.append([brand])

    car_brands_ws = wb.create_sheet("Car Brands")
    car_brands_ws.append(["Car Brand"])
    for make in CarMake.objects.order_by("name"):
        car_brands_ws.append([make.name])

    car_models_ws = wb.create_sheet("Car Models")
    car_models_ws.append(["Car Brand", "Car Model", "Year From", "Year To", "Engine", "Chassis Prefixes"])
    for model in CarModel.objects.select_related("make").order_by("make__name", "name"):
        car_models_ws.append([
            model.make.name,
            model.name,
            model.year_from or "",
            model.year_to or "",
            model.engine_type or "",
            model.chassis_prefixes or "",
        ])

    for attribute_ws in (categories_ws, brands_ws, car_brands_ws, car_models_ws):
        attribute_ws.freeze_panes = "A2"
        attribute_ws.auto_filter.ref = attribute_ws.dimensions
        for cell in attribute_ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for col in range(1, attribute_ws.max_column + 1):
            attribute_ws.column_dimensions[get_column_letter(col)].width = 24

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="inventory_export.xlsx"'
    wb.save(response)
    return response


@login_required
def import_inventory(request):
    """Import products from uploaded Excel file."""
    if request.method != "POST":
        return render(request, "inventory/import_inventory.html")

    excel_file = request.FILES.get("file")
    if not excel_file:
        return render(request, "inventory/import_inventory.html", {
            "error": "Please select an Excel file to upload."
        })

    if not excel_file.name.endswith(".xlsx"):
        return render(request, "inventory/import_inventory.html", {
            "error": "Invalid file type. Please upload an .xlsx file."
        })

    try:
        wb = load_workbook(excel_file, read_only=True, data_only=True)
        ws = wb["Inventory"] if "Inventory" in wb.sheetnames else wb.active

        if "Categories" in wb.sheetnames:
            for row in wb["Categories"].iter_rows(min_row=2, values_only=True):
                category_name = str(row[0] or "").strip() if row else ""
                if category_name:
                    Category.objects.get_or_create(name=category_name[:100])

        if "Car Brands" in wb.sheetnames:
            for row in wb["Car Brands"].iter_rows(min_row=2, values_only=True):
                make_name = str(row[0] or "").strip() if row else ""
                if make_name:
                    CarMake.objects.get_or_create(name=make_name[:100])

        if "Car Models" in wb.sheetnames:
            car_models_ws = wb["Car Models"]
            car_model_headers = {
                " ".join(str(value).strip().casefold().split()): index
                for index, value in enumerate(next(
                    car_models_ws.iter_rows(min_row=1, max_row=1, values_only=True), ()
                ))
                if value is not None and str(value).strip()
            }
            for row in car_models_ws.iter_rows(min_row=2, values_only=True):
                def lookup_value(*names):
                    for name in names:
                        index = car_model_headers.get(name.casefold())
                        if index is not None and index < len(row):
                            return row[index]
                    return None

                make_name = str(lookup_value("car brand", "make", "brand") or "").strip()
                model_name = str(lookup_value("car model", "model", "name") or "").strip()
                if not make_name or not model_name:
                    continue
                make, _ = CarMake.objects.get_or_create(name=make_name[:100])
                year_from = lookup_value("year from")
                year_to = lookup_value("year to")
                try:
                    year_from = int(year_from) if year_from not in (None, "") else None
                    year_to = int(year_to) if year_to not in (None, "") else None
                except (TypeError, ValueError):
                    continue
                model_query = CarModel.objects.filter(make=make, name=model_name[:100])
                if year_from is None:
                    model_query = model_query.filter(year_from__isnull=True)
                else:
                    model_query = model_query.filter(year_from=year_from)
                if year_to is None:
                    model_query = model_query.filter(year_to__isnull=True)
                else:
                    model_query = model_query.filter(year_to=year_to)
                model = model_query.first()
                model_defaults = {
                    "year_from": year_from,
                    "year_to": year_to,
                    "engine_type": str(lookup_value("engine") or "")[:100],
                    "chassis_prefixes": str(lookup_value("chassis prefixes") or "")[:200],
                }
                if model:
                    for field, value in model_defaults.items():
                        setattr(model, field, value)
                    model.save()
                else:
                    CarModel.objects.create(
                        make=make,
                        name=model_name[:100],
                        **model_defaults,
                    )

        first_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
        first_cell = str(first_row[0] or "").upper() if first_row else ""
        header_columns = {
            " ".join(str(value).strip().casefold().split()): index
            for index, value in enumerate(first_row)
            if value is not None and str(value).strip()
        }

        def column_value(row, names, fallback_index=None):
            for name in names:
                index = header_columns.get(" ".join(name.strip().casefold().split()))
                if index is not None and index < len(row):
                    return row[index]
            if fallback_index is not None and fallback_index < len(row):
                return row[fallback_index]
            return None

        # Detect format: "PART NAME" in header = spare parts format (INVENTORY.xlsx)
        is_spare_parts_format = first_cell and "PART NAME" in first_cell

        imported = 0
        errors = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            if not row or not any(row):
                continue

            sku_value = None
            manufacturer = ""
            is_genuine = True
            unit = "PCS"
            cost_price = 0
            wholesale_price = 0
            reorder_level = 0
            shelf_bin = ""
            alternate_numbers = ""
            car_brand_value = ""
            car_model_value = ""

            if is_spare_parts_format:
                name = str(row[0] or "").strip() if row[0] is not None else ""
                part_num_col_b = row[1]
                qty = row[4] if len(row) > 4 else None
                inside_part = str(row[5] or "").strip() if len(row) > 5 and row[5] else ""
                brand = str(row[6] or "").strip() if len(row) > 6 and row[6] else ""
                type_name = str(row[7] or "").strip() if len(row) > 7 and row[7] else ""
                purpose = str(row[8] or "").strip() if len(row) > 8 and row[8] else ""
                car_used = str(row[9] or "").strip() if len(row) > 9 and row[9] else ""

                # Skip section header rows (e.g. B0, C0, D0) - only col A has value
                if name and not any([part_num_col_b, qty, inside_part, brand, type_name]):
                    continue

                if not name:
                    continue

                part_number = inside_part or str(part_num_col_b or "").strip()
                sku_value = None
                manufacturer = ""
                is_genuine = True
                unit = "PCS"
                cost_price = 0
                wholesale_price = 0
                reorder_level = 0
                shelf_bin = ""
                alternate_numbers = ""
                quantity = qty or 0
                category_name = type_name
                vehicle_app = car_used
                location = ""
                purpose_val = purpose
                selling_price = 0
            else:
                part_number_value = column_value(row, ("part number", "part #", "part no"))
                name_value = column_value(row, ("product name", "name", "part name"), 1)
                sku_value = column_value(row, ("sku",))
                part_number = str(part_number_value or "").strip()
                name = str(name_value or "").strip()
                if not name:
                    errors.append(f"Row {row_num}: Name is required.")
                    continue
                def value(*names, fallback=None):
                    return column_value(row, names, fallback)

                brand = str(value("brand", "mark", fallback=2) or "").strip()
                manufacturer = str(value("manufacturer / origin", "manufacturer", "origin") or "").strip()
                genuine_value = value("genuine oem", "genuine", "is genuine")
                if isinstance(genuine_value, str):
                    is_genuine = genuine_value.strip().casefold() in {"yes", "true", "1", "genuine"}
                else:
                    is_genuine = bool(genuine_value) if genuine_value is not None else True
                category_name = str(value("category", "type", fallback=3) or "").strip()
                unit = str(value("unit of measure", "unit") or "PCS").strip().upper()
                if unit not in dict(Product.UOM_CHOICES):
                    unit_label_to_code = {
                        label.casefold(): code for code, label in Product.UOM_CHOICES
                    }
                    unit = unit_label_to_code.get(unit.casefold(), "PCS")

                quantity_value = value(
                    "stock quantity", "available stock", "quantity", "qty", "stock", fallback=4
                )
                reorder_value = value("minimum stock", "reorder level")
                cost_value = value("cost price", "cost")
                selling_price_value = value("selling price", "price", fallback=5)
                wholesale_value = value("wholesale price",)
                location_value = value("storage location", "location", fallback=6)
                shelf_bin_value = value("shelf / bin", "shelf/bin", "shelf bin")
                purpose_value = value("purpose", "remarks")
                vehicle_value = value(
                    "vehicle application",
                    "vehicle/car types / chassis",
                    "vehicle",
                    "car types",
                )
                car_brand_value = value("car brand",)
                car_model_value = value("car model",)
                alternate_value = value("alternate part numbers", "alternate numbers", "cross reference")

                def number(raw_value, field_name, default=0, integer=False):
                    if raw_value in (None, ""):
                        return default
                    try:
                        parsed = float(raw_value)
                        if parsed < 0 or (integer and not parsed.is_integer()):
                            raise ValueError
                        return int(parsed) if integer else parsed
                    except (TypeError, ValueError):
                        raise ValueError(f"Row {row_num}: {field_name} must be a non-negative {'whole number' if integer else 'number'}.")

                try:
                    quantity = number(quantity_value, "Stock Quantity", integer=True)
                    reorder_level = number(reorder_value, "Minimum Stock", integer=True)
                    cost_price = number(cost_value, "Cost Price")
                    selling_price = number(selling_price_value, "Selling Price")
                    wholesale_price = number(wholesale_value, "Wholesale Price")
                except ValueError as exc:
                    errors.append(str(exc))
                    continue
                brand = brand[:50]
                category_name = category_name[:100]
                location = str(location_value or "").strip()
                shelf_bin = str(shelf_bin_value or "").strip()
                purpose_val = str(purpose_value or "").strip()
                vehicle_app = str(vehicle_value or "").strip()
                alternate_numbers = str(alternate_value or "").strip()

            category = None
            if category_name:
                category, _ = Category.objects.get_or_create(name=category_name)

            imported_sku = str(sku_value or "").strip()[:50] if sku_value is not None else ""
            product = None
            if imported_sku:
                product = Product.objects.filter(sku=imported_sku).first()
            if product is None and part_number:
                product = Product.objects.filter(part_number=part_number).first()

            conflicting_sku = Product.objects.filter(sku=imported_sku)
            if imported_sku and product:
                conflicting_sku = conflicting_sku.exclude(pk=product.pk)
            if imported_sku and conflicting_sku.exists():
                errors.append(f"Row {row_num}: SKU '{imported_sku}' already belongs to another product.")
                continue

            product_values = {
                "part_number": part_number[:50],
                "name": name[:100],
                "brand": brand[:50],
                "manufacturer_brand": manufacturer[:100],
                "is_genuine": is_genuine,
                "category": category,
                "unit_of_measure": unit,
                "quantity": max(0, quantity),
                "reorder_level": max(0, reorder_level),
                "cost_price": max(0, cost_price),
                "selling_price": max(0, selling_price),
                "wholesale_price": max(0, wholesale_price),
                "location": location[:150] if location else "",
                "shelf_bin": shelf_bin[:50],
                "purpose": purpose_val[:150] if purpose_val else "",
                "vehicle_application": vehicle_app[:500] if vehicle_app else "",
                "alternate_numbers": alternate_numbers[:255],
            }
            if product:
                if not is_spare_parts_format:
                    optional_headers = {
                        "part_number": ("part number", "part #", "part no"),
                        "manufacturer_brand": ("manufacturer / origin", "manufacturer", "origin"),
                        "is_genuine": ("genuine oem", "genuine", "is genuine"),
                        "unit_of_measure": ("unit of measure", "unit"),
                        "cost_price": ("cost price", "cost"),
                        "selling_price": ("selling price", "price"),
                        "wholesale_price": ("wholesale price",),
                        "reorder_level": ("minimum stock", "reorder level"),
                        "shelf_bin": ("shelf / bin", "shelf/bin", "shelf bin"),
                        "alternate_numbers": ("alternate part numbers", "alternate numbers", "cross reference"),
                    }
                    for field, aliases in optional_headers.items():
                        if not any(
                            " ".join(alias.casefold().split()) in header_columns
                            for alias in aliases
                        ):
                            product_values.pop(field)
                for field, value in product_values.items():
                    setattr(product, field, value)
                if imported_sku:
                    product.sku = imported_sku
                product.save()
            else:
                product = Product.objects.create(
                    sku=imported_sku or ProductForm.generate_unique_sku(part_number),
                    **product_values,
                )
            compatibility_models = []
            car_brand_names = [value.strip() for value in str(car_brand_value or "").split("|") if value.strip()]
            car_model_names = [value.strip() for value in str(car_model_value or "").split("|") if value.strip()]
            for model_index, model_name in enumerate(car_model_names):
                make_name = car_brand_names[min(model_index, len(car_brand_names) - 1)] if car_brand_names else ""
                model_query = CarModel.objects.select_related("make").all()
                if make_name:
                    model_query = model_query.filter(make__name__iexact=make_name)
                model = next(
                    (
                        candidate for candidate in model_query
                        if candidate.name.casefold() == model_name.casefold()
                        or str(candidate).casefold() == model_name.casefold()
                    ),
                    None,
                )
                if not model:
                    errors.append(
                        f"Row {row_num}: Car model '{model_name}'"
                        f"{f' for {make_name}' if make_name else ''} was not found in the Car Models list."
                    )
                    continue
                compatibility_models.append(model)
            if compatibility_models or car_model_names:
                product.compatibilities.set(compatibility_models)
            imported += 1

        wb.close()

        return render(request, "inventory/import_inventory.html", {
            "success": f"Successfully imported or updated {imported} product(s).",
            "errors": errors if errors else None,
        })

    except Exception as e:
        return render(request, "inventory/import_inventory.html", {
            "error": f"Import failed: {str(e)}"
        })


@login_required
def warehouse_list(request):
    """
    Multi-Shop & Warehouse Management Hub.
    Displays all shops and stores with branch stock summaries, total valuation,
    and individual parts inventory per location.
    """
    from .models import Warehouse, ProductBranchStock, Product
    warehouses = Warehouse.objects.prefetch_related("product_stocks__product").all()
    selected_wh_id = request.GET.get("wh")
    selected_warehouse = None
    branch_stocks = None
    
    if selected_wh_id and selected_wh_id.isdigit():
        selected_warehouse = warehouses.filter(id=int(selected_wh_id)).first()
        if selected_warehouse:
            branch_stocks = ProductBranchStock.objects.filter(
                warehouse=selected_warehouse, quantity__gt=0
            ).select_related("product__category")

    return render(request, "inventory/warehouse_list.html", {
        "warehouses": warehouses,
        "selected_warehouse": selected_warehouse,
        "branch_stocks": branch_stocks,
    })


@login_required
def transfer_stock(request):
    """
    Transfer spare parts stock between different shops and warehouses.
    """
    from .models import Warehouse, Product, ProductBranchStock, StockMovement

    warehouses = Warehouse.objects.filter(is_active=True).order_by("name")
    products = Product.objects.all().order_by("name")

    if request.method == "POST":
        source_id = request.POST.get("source_warehouse")
        dest_id = request.POST.get("destination_warehouse")
        prod_id = request.POST.get("product_id")
        qty_str = request.POST.get("quantity", "1")
        notes = request.POST.get("notes", "").strip()

        try:
            qty = float(qty_str)
        except (ValueError, TypeError):
            qty = 0

        if not source_id or not dest_id or not prod_id or qty <= 0:
            messages.error(request, "Please fill in all transfer fields with a valid quantity.")
            return redirect("transfer_stock")

        if source_id == dest_id:
            messages.error(request, "Source shop/warehouse and destination cannot be identical.")
            return redirect("transfer_stock")

        source_wh = get_object_or_404(Warehouse, id=source_id)
        dest_wh = get_object_or_404(Warehouse, id=dest_id)
        product = get_object_or_404(Product, id=prod_id)

        # Check source branch stock
        source_stock, _ = ProductBranchStock.objects.get_or_create(
            product=product, warehouse=source_wh, defaults={"quantity": 0}
        )

        if source_stock.quantity < qty:
            messages.error(
                request,
                f"Insufficient stock at {source_wh.name}: requested {qty} {product.uom_short}, but only {source_stock.quantity} available."
            )
            return redirect("transfer_stock")

        with transaction.atomic():
            # Deduct from source branch
            source_stock.quantity -= qty
            source_stock.save()

            # Add to destination branch
            dest_stock, _ = ProductBranchStock.objects.get_or_create(
                product=product, warehouse=dest_wh, defaults={"quantity": 0}
            )
            dest_stock.quantity += qty
            dest_stock.save()

            # Record stock movements
            ref_txt = f"Transfer from {source_wh.name} to {dest_wh.name}"
            if notes:
                ref_txt += f" ({notes})"

            StockMovement.objects.create(
                product=product,
                quantity=-int(qty),
                movement_type="transfer",
                reference=ref_txt,
                warehouse=source_wh,
            )
            StockMovement.objects.create(
                product=product,
                quantity=int(qty),
                movement_type="transfer",
                reference=ref_txt,
                warehouse=dest_wh,
            )

        messages.success(
            request,
            f"Successfully transferred {qty} {product.uom_short} of {product.name} from {source_wh.name} to {dest_wh.name}!"
        )
        return redirect("warehouse_list")

    return render(request, "inventory/transfer_stock.html", {
        "warehouses": warehouses,
        "products": products,
    })


@login_required
def stockmovement_list(request):
    """Display all stock movements with optional filters."""
    from .models import StockMovement
    movements = StockMovement.objects.select_related("product", "warehouse").order_by("-timestamp")
    # simple filtering by type or product name
    mtype = request.GET.get("type", "")
    if mtype:
        movements = movements.filter(movement_type=mtype)
    q = request.GET.get("q", "").strip()
    if q:
        movements = movements.filter(
            Q(product__name__icontains=q) | Q(reference__icontains=q)
        )
    paginator = Paginator(movements, 25)
    page = paginator.get_page(request.GET.get("page", 1))
    return render(request, "inventory/stockmovement_list.html", {"page": page, "filter_type": mtype, "search": q})




@login_required
def attributes_dashboard(request):
    from .models import Category, CarMake, CarModel
    return render(request, "inventory/attributes.html", {
        "category_count": Category.objects.count(),
        "make_count": CarMake.objects.count(),
        "model_count": CarModel.objects.count(),
    })


@login_required
def purchase_list(request):
    """List all purchases with date filter."""
    from django.db.models import Sum

    purchases = Purchase.objects.prefetch_related("items").select_related("supplier").order_by("-date")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    warehouse_id = request.GET.get("warehouse", "")
    if date_from:
        purchases = purchases.filter(date__date__gte=date_from)
    if date_to:
        purchases = purchases.filter(date__date__lte=date_to)
    if warehouse_id:
        purchases = purchases.filter(warehouse_id=warehouse_id)
    total_bought = sum(p.total_amount for p in purchases)
    # supply warehouses for filter dropdown
    from .models import Warehouse
    warehouses = Warehouse.objects.all().order_by("name")
    return render(request, "inventory/purchase_list.html", {
        "purchases": purchases,
        "date_from": date_from,
        "date_to": date_to,
        "total_bought": total_bought,
        "warehouses": warehouses,
        "filter_warehouse": warehouse_id,
    })


@login_required
def parts_analysis(request):
    """Record receipt-backed purchases or sales and summarize part movement."""
    from django.db.models import Sum
    from django.db.models.functions import Coalesce, TruncDate
    from django.core.paginator import Paginator
    from django.utils import timezone
    from django.utils.dateparse import parse_date
    from sales.models import Customer, Sale, SaleItem

    max_receipt_size = 10 * 1024 * 1024
    products = list(Product.objects.order_by("name"))
    suppliers = list(Supplier.objects.order_by("name"))
    warehouses = list(Warehouse.objects.order_by("name"))
    errors = []
    line_rows = [{"product_id": "", "quantity": "", "unit_price": ""}]
    date_from_text = request.GET.get("date_from", "").strip()
    date_to_text = request.GET.get("date_to", "").strip()
    search_text = request.GET.get("q", "").strip()
    date_from = parse_date(date_from_text) if date_from_text else None
    date_to = parse_date(date_to_text) if date_to_text else None

    if date_from_text and date_from is None:
        errors.append("Enter a valid start date.")
    if date_to_text and date_to is None:
        errors.append("Enter a valid end date.")
    if date_from and date_to and date_from > date_to:
        errors.append("Start date must be on or before end date.")

    purchases = Purchase.objects.select_related("supplier", "recorded_by").prefetch_related("items__product")
    sales = Sale.objects.select_related("customer", "cashier").prefetch_related("items__product")
    if date_from:
        purchases = purchases.filter(
            Q(document_date__gte=date_from)
            | Q(document_date__isnull=True, date__date__gte=date_from)
        )
        sales = sales.filter(
            Q(document_date__gte=date_from)
            | Q(document_date__isnull=True, date__date__gte=date_from)
        )
    if date_to:
        purchases = purchases.filter(
            Q(document_date__lte=date_to)
            | Q(document_date__isnull=True, date__date__lte=date_to)
        )
        sales = sales.filter(
            Q(document_date__lte=date_to)
            | Q(document_date__isnull=True, date__date__lte=date_to)
        )
    if search_text:
        purchases = purchases.filter(
            Q(invoice_number__icontains=search_text)
            | Q(supplier__name__icontains=search_text)
            | Q(source_text__icontains=search_text)
            | Q(items__product__name__icontains=search_text)
            | Q(items__product__part_number__icontains=search_text)
            | Q(items__product__sku__icontains=search_text)
        ).distinct()
        sales = sales.filter(
            Q(receipt_reference__icontains=search_text)
            | Q(fs_number__icontains=search_text)
            | Q(customer__name__icontains=search_text)
            | Q(customer__company_name__icontains=search_text)
            | Q(source_text__icontains=search_text)
            | Q(items__product__name__icontains=search_text)
            | Q(items__product__part_number__icontains=search_text)
            | Q(items__product__sku__icontains=search_text)
        ).distinct()

    def page_context():
        audit_params = request.GET.copy()
        audit_params.pop("purchase_page", None)
        audit_params.pop("sale_page", None)
        purchase_page = Paginator(
            purchases.annotate(audit_date=Coalesce("document_date", TruncDate("date")))
            .order_by("-audit_date", "-date"),
            25,
        ).get_page(request.GET.get("purchase_page", 1))
        sale_page = Paginator(
            sales.annotate(audit_date=Coalesce("document_date", TruncDate("date")))
            .order_by("-audit_date", "-date"),
            25,
        ).get_page(request.GET.get("sale_page", 1))
        bought_totals = dict(
            PurchaseItem.objects.filter(purchase__in=purchases.values("pk")).values("product_id")
            .annotate(total=Sum("quantity"))
            .values_list("product_id", "total")
        )
        sold_totals = dict(
            SaleItem.objects.filter(sale__in=sales.values("pk")).values("product_id")
            .annotate(total=Sum("quantity"))
            .values_list("product_id", "total")
        )
        for product in products:
            product.total_bought = bought_totals.get(product.id, 0)
            product.total_sold = sold_totals.get(product.id, 0)
        return {
            "products": products,
            "suppliers": suppliers,
            "warehouses": warehouses,
            "payment_method_choices": Sale.PAYMENT_METHOD_CHOICES,
            "line_rows": line_rows,
            "errors": errors,
            "recent_purchases": purchase_page,
            "recent_sales": sale_page,
            "audit_query": audit_params.urlencode(),
            "date_from": date_from_text,
            "date_to": date_to_text,
            "search_text": search_text,
            "today": timezone.localdate().isoformat(),
        }

    if request.method == "POST":
        entry_type = request.POST.get("entry_type", "")
        reference = request.POST.get("reference", "").strip()
        document_date_text = request.POST.get("document_date", "").strip()
        document_date = parse_date(document_date_text)
        party_name = request.POST.get("party_name", "").strip()
        source_text = request.POST.get("source_text", "").strip()
        receipt_file = request.FILES.get("receipt_file")
        product_ids = request.POST.getlist("product_id[]")
        quantities = request.POST.getlist("quantity[]")
        unit_prices = request.POST.getlist("unit_price[]")
        line_rows = [
            {
                "product_id": product_id,
                "quantity": quantities[index] if index < len(quantities) else "",
                "unit_price": unit_prices[index] if index < len(unit_prices) else "",
            }
            for index, product_id in enumerate(product_ids)
        ] or [{"product_id": "", "quantity": "", "unit_price": ""}]

        if entry_type not in {"purchase", "sale"}:
            errors.append("Choose whether this receipt records parts bought or sold.")
        if not reference:
            errors.append("Enter the receipt or invoice number so it can be audited.")
        if len(reference) > 100:
            errors.append("Receipt or invoice number must be no more than 100 characters.")
        if not document_date:
            errors.append("Enter the date printed on the receipt.")
        if entry_type == "purchase" and len(party_name) > 100:
            errors.append("Supplier name must be no more than 100 characters.")
        if entry_type == "sale" and len(party_name) > 150:
            errors.append("Buyer name must be no more than 150 characters.")
        if not receipt_file and not source_text:
            errors.append("Attach the paper/photo/PDF or enter its text before recording the transaction.")
        if len(source_text) > 20000:
            errors.append("Receipt text must be no more than 20,000 characters.")
        if receipt_file:
            extension = Path(receipt_file.name).suffix.lower()
            if extension not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                errors.append("Receipt files must be PDF or image files (PNG, JPG, WEBP, or GIF).")
            if receipt_file.size > max_receipt_size:
                errors.append("Receipt files must be 10 MB or smaller.")
        warehouse_id = request.POST.get("warehouse_id", "").strip()
        if warehouse_id and (
            not warehouse_id.isdigit() or not Warehouse.objects.filter(pk=warehouse_id).exists()
        ):
            errors.append("Select a valid warehouse or branch.")

        parsed_lines = []
        max_rows = max(len(product_ids), len(quantities), len(unit_prices))
        for index in range(max_rows):
            product_id = product_ids[index] if index < len(product_ids) else ""
            quantity_value = quantities[index] if index < len(quantities) else ""
            price_value = unit_prices[index] if index < len(unit_prices) else ""
            if not product_id and not quantity_value and not price_value:
                continue
            if not product_id or not product_id.isdigit():
                errors.append(f"Line {index + 1}: select a valid part.")
                continue
            try:
                quantity = int(quantity_value)
                unit_price = Decimal(price_value)
                if (
                    quantity <= 0
                    or quantity > 2147483647
                    or not unit_price.is_finite()
                    or unit_price <= 0
                    or unit_price > Decimal("9999999999.99")
                ):
                    raise ValueError
            except (ValueError, InvalidOperation):
                errors.append(f"Line {index + 1}: enter a quantity and unit price greater than zero.")
                continue
            try:
                product = Product.objects.get(pk=int(product_id))
            except Product.DoesNotExist:
                errors.append(f"Line {index + 1}: the selected part no longer exists.")
                continue
            parsed_lines.append((product, quantity, unit_price))

        if not parsed_lines:
            errors.append("Add at least one valid part line.")
        if entry_type == "sale":
            payment_method = request.POST.get("payment_method", "CASH")
            valid_payment_methods = {choice[0] for choice in Sale.PAYMENT_METHOD_CHOICES}
            if payment_method not in valid_payment_methods:
                errors.append("Choose a valid sale payment method.")

        if entry_type == "sale" and not errors:
            requested_by_product = {}
            for product, quantity, _ in parsed_lines:
                requested_by_product[product.id] = requested_by_product.get(product.id, 0) + quantity
            for product in products:
                requested = requested_by_product.get(product.id, 0)
                if requested > product.quantity:
                    errors.append(
                        f"Not enough stock for {product.name}: requested {requested}, "
                        f"only {product.quantity} available."
                    )

        if not errors:
            with transaction.atomic():
                if entry_type == "sale":
                    requested_by_product = {}
                    for product, quantity, _ in parsed_lines:
                        requested_by_product[product.id] = requested_by_product.get(product.id, 0) + quantity
                    locked_quantities = dict(
                        Product.objects.select_for_update()
                        .filter(pk__in=requested_by_product)
                        .values_list("pk", "quantity")
                    )
                    for product, requested in requested_by_product.items():
                        available = locked_quantities.get(product, 0)
                        if requested > available:
                            product_name = next(item.name for item, _, _ in parsed_lines if item.id == product)
                            errors.append(
                                f"Not enough stock for {product_name}: requested {requested}, "
                                f"only {available} available."
                            )
                    if errors:
                        context = page_context()
                        context.update({
                            "entry_type": entry_type,
                            "reference": reference,
                            "document_date": document_date_text,
                            "party_name": party_name,
                            "source_text": source_text,
                            "selected_warehouse": request.POST.get("warehouse_id", ""),
                            "selected_payment_method": payment_method,
                            "errors": errors,
                        })
                        return render(request, "inventory/parts_analysis.html", context)

                if entry_type == "purchase":
                    supplier = None
                    if party_name:
                        supplier = Supplier.objects.filter(name__iexact=party_name).first()
                        if supplier is None:
                            supplier = Supplier.objects.create(name=party_name)
                    warehouse = Warehouse.objects.filter(pk=warehouse_id).first() if warehouse_id.isdigit() else None
                    purchase = Purchase.objects.create(
                        supplier=supplier,
                        warehouse=warehouse,
                        invoice_number=reference,
                        document_date=document_date,
                        notes="Entered using Parts Analysis",
                        source_text=source_text,
                        receipt_file=receipt_file,
                        recorded_by=request.user,
                    )
                    total = Decimal("0")
                    for product, quantity, unit_cost in parsed_lines:
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            product=product,
                            quantity=quantity,
                            unit_cost=float(unit_cost),
                        )
                        total += quantity * unit_cost
                    purchase.total_amount = float(total)
                    purchase.save(update_fields=["total_amount"])
                    messages.success(request, f"Purchase #{purchase.id} recorded and stock updated.")
                else:
                    customer = None
                    if party_name:
                        customer = Customer.objects.filter(
                            Q(company_name__iexact=party_name) | Q(name__iexact=party_name)
                        ).first()
                        if customer is None:
                            customer = Customer.objects.create(name=party_name[:100], company_name=party_name)
                    warehouse = Warehouse.objects.filter(pk=warehouse_id).first() if warehouse_id.isdigit() else None
                    sale = Sale.objects.create(
                        payment_method=request.POST.get("payment_method", "CASH"),
                        customer=customer,
                        warehouse=warehouse,
                        cashier=request.user,
                        receipt_reference=reference,
                        document_date=document_date,
                        receipt_file=receipt_file,
                        source_text=source_text,
                    )
                    total = Decimal("0")
                    for product, quantity, unit_price in parsed_lines:
                        SaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=quantity,
                            price=float(unit_price),
                            cost_price=product.cost_price,
                        )
                        total += quantity * unit_price
                    sale.total_amount = float(total)
                    sale.subtotal_amount = round(float(total / Decimal("1.15")), 2)
                    sale.tax_amount = round(float(total) - sale.subtotal_amount, 2)
                    sale.fs_number = f"FS-{sale.id:06d}"
                    sale.save(update_fields=["total_amount", "subtotal_amount", "tax_amount", "fs_number"])
                    messages.success(request, f"Sale #{sale.id} recorded and stock updated.")
                return redirect("parts_analysis")

        context = page_context()
        context["entry_type"] = entry_type
        context["reference"] = reference
        context["document_date"] = document_date_text
        context["party_name"] = party_name
        context["source_text"] = source_text
        context["selected_warehouse"] = request.POST.get("warehouse_id", "")
        context["selected_payment_method"] = request.POST.get("payment_method", "CASH")
        context["errors"] = errors
        return render(request, "inventory/parts_analysis.html", context)

    return render(request, "inventory/parts_analysis.html", page_context())


@login_required
def purchase_add(request):
    """Add a new purchase (bought items) with existing or newly created products."""
    from .models import Warehouse
    from django.contrib import messages
    from django.utils import timezone
    from django.utils.dateparse import parse_date

    products = Product.objects.select_related("category").order_by("name")
    suppliers = Supplier.objects.order_by("name")
    categories = Category.objects.order_by("name")
    warehouses = Warehouse.objects.order_by("name")

    if request.method == "POST":
        supplier_id = request.POST.get("supplier") or None
        warehouse_id = request.POST.get("warehouse") or None
        notes = request.POST.get("notes", "").strip()
        invoice_number = request.POST.get("invoice_number", "").strip()
        receipt_file = request.FILES.get("purchase_receipt")
        document_date_text = request.POST.get("document_date", "").strip()
        document_date = parse_date(document_date_text) if document_date_text else timezone.localdate()
        if document_date is None:
            messages.error(request, "Enter a valid supplier receipt date.")
            return render(request, "inventory/purchase_add.html", {
                "products": products,
                "suppliers": suppliers,
                "categories": categories,
                "warehouses": warehouses,
                "today": timezone.localdate().isoformat(),
            })

        supplier = Supplier.objects.get(pk=supplier_id) if supplier_id else None
        warehouse = Warehouse.objects.get(pk=warehouse_id) if warehouse_id else None

        with transaction.atomic():
            purchase = Purchase.objects.create(
                supplier=supplier,
                warehouse=warehouse,
                notes=notes,
                invoice_number=invoice_number,
                document_date=document_date,
                receipt_file=receipt_file,
                recorded_by=request.user,
            )

            total = 0.0
            items_added = 0

            # Process dynamic line items if submitted
            item_types = request.POST.getlist("item_type[]")

            if item_types:
                existing_product_ids = request.POST.getlist("existing_product_id[]")
                existing_qtys = request.POST.getlist("existing_qty[]")
                existing_costs = request.POST.getlist("existing_cost[]")

                new_names = request.POST.getlist("new_name[]")
                new_skus = request.POST.getlist("new_sku[]")
                new_part_numbers = request.POST.getlist("new_part_number[]")
                new_category_ids = request.POST.getlist("new_category_id[]")
                new_brands = request.POST.getlist("new_brand[]")
                new_costs = request.POST.getlist("new_cost[]")
                new_selling_prices = request.POST.getlist("new_selling_price[]")
                new_locations = request.POST.getlist("new_location[]")
                new_qtys = request.POST.getlist("new_qty[]")

                existing_idx = 0
                new_idx = 0

                for itype in item_types:
                    if itype == "existing":
                        if existing_idx < len(existing_product_ids):
                            prod_id = existing_product_ids[existing_idx]
                            qty_val = int(existing_qtys[existing_idx] or 0) if existing_idx < len(existing_qtys) else 0
                            cost_val = float(existing_costs[existing_idx] or 0) if existing_idx < len(existing_costs) else 0.0
                            existing_idx += 1

                            if prod_id and qty_val > 0:
                                try:
                                    product = Product.objects.get(pk=prod_id)
                                    PurchaseItem.objects.create(
                                        purchase=purchase,
                                        product=product,
                                        quantity=qty_val,
                                        unit_cost=cost_val,
                                    )
                                    total += qty_val * cost_val
                                    items_added += 1
                                except Product.DoesNotExist:
                                    pass

                    elif itype == "new":
                        if new_idx < len(new_names):
                            p_name = new_names[new_idx].strip()
                            p_sku = new_skus[new_idx].strip() if new_idx < len(new_skus) else ""
                            p_part = new_part_numbers[new_idx].strip() if new_idx < len(new_part_numbers) else ""
                            p_cat_id = new_category_ids[new_idx] if new_idx < len(new_category_ids) else ""
                            p_brand = new_brands[new_idx].strip() if new_idx < len(new_brands) else ""
                            cost_val = float(new_costs[new_idx] or 0) if new_idx < len(new_costs) else 0.0
                            sell_val = float(new_selling_prices[new_idx] or 0) if new_idx < len(new_selling_prices) else cost_val
                            p_loc = new_locations[new_idx].strip() if new_idx < len(new_locations) else ""
                            qty_val = int(new_qtys[new_idx] or 0) if new_idx < len(new_qtys) else 0
                            new_idx += 1

                            if p_name and qty_val > 0:
                                p_cat = Category.objects.get(pk=p_cat_id) if p_cat_id else None
                                product = Product.objects.create(
                                    sku=p_sku,
                                    part_number=p_part,
                                    name=p_name,
                                    category=p_cat,
                                    brand=p_brand,
                                    cost_price=cost_val,
                                    selling_price=sell_val,
                                    location=p_loc,
                                    quantity=0,
                                )
                                PurchaseItem.objects.create(
                                    purchase=purchase,
                                    product=product,
                                    quantity=qty_val,
                                    unit_cost=cost_val,
                                )
                                total += qty_val * cost_val
                                items_added += 1

            # Fallback loop for legacy static form input format
            else:
                for product in products:
                    qty = int(request.POST.get(f"qty_{product.id}", 0) or 0)
                    if qty > 0:
                        unit_cost = float(request.POST.get(f"cost_{product.id}", 0) or product.cost_price or 0)
                        PurchaseItem.objects.create(
                            purchase=purchase,
                            product=product,
                            quantity=qty,
                            unit_cost=unit_cost,
                        )
                        total += qty * unit_cost
                        items_added += 1

            purchase.total_amount = total
            purchase.save()
            messages.success(request, f"Purchase #{purchase.id} created successfully with {items_added} item(s).")
            
        return redirect("purchase_list")

    return render(request, "inventory/purchase_add.html", {
        "products": products,
        "suppliers": suppliers,
        "categories": categories,
        "warehouses": warehouses,
        "today": timezone.localdate().isoformat(),
    })


# =====================================================================
# IMPORT MATERIALS & LANDED COST CALCULATION SYSTEM (የውጭ ዕቃዎች ማስገቢያ)
# =====================================================================

@login_required
def import_shipments_list(request):
    """
    Overview of all international material/spare parts import shipments,
    tracking freight, customs clearance, and landed costs in ETB.
    """
    from .models import ImportShipment
    shipments = ImportShipment.objects.select_related("supplier", "destination_warehouse").prefetch_related("items").order_by("-order_date")
    return render(request, "inventory/import_shipments_list.html", {
        "shipments": shipments,
    })


@login_required
def import_shipment_create(request):
    """
    Create a new international import shipment and calculate landed cost per unit in ETB.
    Apportions shipping, insurance, customs duty, and port handling across items.
    """
    from .models import ImportShipment, ImportShipmentItem, Supplier, Warehouse, Product

    suppliers = Supplier.objects.all().order_by("name")
    warehouses = Warehouse.objects.filter(is_active=True).order_by("name")
    products = Product.objects.all().order_by("name")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        supplier_id = request.POST.get("supplier_id")
        warehouse_id = request.POST.get("warehouse_id")
        origin_country = request.POST.get("origin_country", "China").strip()
        departure_port = request.POST.get("departure_port", "").strip()
        arrival_port = request.POST.get("arrival_port", "Modjo Dry Port").strip()
        currency = request.POST.get("currency", "USD").strip()
        
        try:
            exchange_rate = float(request.POST.get("exchange_rate", "135.0") or 135.0)
        except ValueError:
            exchange_rate = 135.0

        try:
            freight = float(request.POST.get("freight_cost_etb", "0") or 0.0)
            insurance = float(request.POST.get("insurance_cost_etb", "0") or 0.0)
            customs_duty = float(request.POST.get("customs_duty_etb", "0") or 0.0)
            port_handling = float(request.POST.get("port_handling_etb", "0") or 0.0)
            inland_transport = float(request.POST.get("inland_transport_etb", "0") or 0.0)
            other_clearing = float(request.POST.get("other_clearing_costs_etb", "0") or 0.0)
        except ValueError:
            freight = insurance = customs_duty = port_handling = inland_transport = other_clearing = 0.0

        bill_of_lading = request.POST.get("bill_of_lading", "").strip()
        notes = request.POST.get("notes", "").strip()

        # Sequential shipment code: IMP-YYYY-XXXX
        year_str = timezone.now().strftime("%Y")
        count = ImportShipment.objects.filter(order_date__year=timezone.now().year).count() + 1
        shipment_num = f"IMP-{year_str}-{count:03d}"

        supplier = Supplier.objects.filter(id=supplier_id).first() if supplier_id else None
        warehouse = Warehouse.objects.filter(id=warehouse_id).first() if warehouse_id else None

        with transaction.atomic():
            shipment = ImportShipment.objects.create(
                shipment_number=shipment_num,
                title=title or f"Import Shipment from {origin_country}",
                supplier=supplier,
                destination_warehouse=warehouse,
                origin_country=origin_country,
                departure_port=departure_port,
                arrival_port=arrival_port,
                currency=currency,
                exchange_rate=exchange_rate,
                freight_cost_etb=freight,
                insurance_cost_etb=insurance,
                customs_duty_etb=customs_duty,
                port_handling_etb=port_handling,
                inland_transport_etb=inland_transport,
                other_clearing_costs_etb=other_clearing,
                bill_of_lading=bill_of_lading,
                notes=notes,
                status="PLANNED",
            )

            # Process items
            prod_ids = request.POST.getlist("item_product_id[]")
            qtys = request.POST.getlist("item_qty[]")
            fob_prices = request.POST.getlist("item_fob_price[]")
            hs_codes = request.POST.getlist("item_hs_code[]")
            target_margins = request.POST.getlist("item_target_price[]")

            for i in range(len(prod_ids)):
                if i < len(prod_ids) and prod_ids[i].isdigit():
                    p = Product.objects.filter(id=int(prod_ids[i])).first()
                    if p:
                        try:
                            q_val = float(qtys[i]) if i < len(qtys) else 1.0
                        except ValueError:
                            q_val = 1.0
                        try:
                            fob_val = float(fob_prices[i]) if i < len(fob_prices) else 0.0
                        except ValueError:
                            fob_val = 0.0
                        hs_val = hs_codes[i].strip() if i < len(hs_codes) else ""
                        try:
                            target_p = float(target_margins[i]) if i < len(target_margins) and target_margins[i] else 0.0
                        except ValueError:
                            target_p = 0.0

                        ImportShipmentItem.objects.create(
                            shipment=shipment,
                            product=p,
                            quantity=q_val,
                            foreign_fob_price=fob_val,
                            customs_tariff_code=hs_val,
                            target_selling_price_etb=target_p,
                        )

            shipment.recalculate_landed_costs()

        messages.success(
            request,
            f"Import Shipment {shipment.shipment_number} created with full landed cost calculations!"
        )
        return redirect("import_shipment_detail", pk=shipment.id)

    return render(request, "inventory/import_shipment_form.html", {
        "suppliers": suppliers,
        "warehouses": warehouses,
        "products": products,
    })


@login_required
def import_shipment_detail(request, pk):
    """
    Detailed Landed Cost Worksheet showing itemized breakdown of FOB price,
    allocated freight, customs duty, port clearance, and final landed unit cost in ETB.
    """
    from .models import ImportShipment
    shipment = get_object_or_404(
        ImportShipment.objects.select_related("supplier", "destination_warehouse").prefetch_related("items__product"),
        id=pk
    )
    return render(request, "inventory/import_shipment_detail.html", {
        "shipment": shipment,
    })


@login_required
def import_shipment_receive(request, pk):
    """
    Receives an arrived import shipment into the designated shop/store, updating product
    cost prices, retail selling prices, and inventory stock counts.
    """
    from .models import ImportShipment
    shipment = get_object_or_404(ImportShipment, id=pk)
    if shipment.status == "ARRIVED":
        messages.info(request, "This shipment has already been received into inventory.")
        return redirect("import_shipment_detail", pk=shipment.id)

    with transaction.atomic():
        shipment.apply_to_inventory()

    messages.success(
        request,
        f"Shipment {shipment.shipment_number} received into {shipment.destination_warehouse.name if shipment.destination_warehouse else 'Inventory'}! Stock quantities and cost prices updated."
    )
    return redirect("import_shipment_detail", pk=shipment.id)
