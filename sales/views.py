from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from expenses.models import Expense
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.core.paginator import Paginator

from inventory.models import Product, CarMake, CarModel
from inventory.fitment import verify_product_fitment
from inventory.cross_reference import find_parts_with_cross_reference, parse_alternate_numbers
from .models import Cart, Sale, SaleItem, Customer, CustomerVehicle, PaymentTransaction

@login_required
@permission_required('sales.add_sale', raise_exception=True)
def create_sale(request):
    ...




@login_required
@login_required
def pos_view(request):
    # list products with prefetching for high performance
    products_qs = Product.objects.select_related('category').prefetch_related('compatibilities__make', 'substitutes__substitute_product')
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    cart_count = sum(item.quantity for item in cart_items)

    q = request.GET.get("q", "").strip()
    vin_query = request.GET.get("vin", "").strip()

    # Customer & Saved Garage Fleet handling
    cust_id = request.GET.get("customer", "").strip()
    active_customer = None
    customer_vehicles = []
    if cust_id.isdigit():
        active_customer = Customer.objects.filter(id=int(cust_id)).first()
        if active_customer:
            customer_vehicles = list(active_customer.vehicles.select_related('car_model', 'car_model__make').all())

    # Selected customer vehicle
    veh_id = request.GET.get("vehicle", "").strip()
    active_vehicle = None
    if veh_id.isdigit():
        active_vehicle = CustomerVehicle.objects.filter(id=int(veh_id)).select_related('car_model', 'car_model__make', 'customer').first()
        if active_vehicle:
            if not active_customer:
                active_customer = active_vehicle.customer
                customer_vehicles = list(active_customer.vehicles.select_related('car_model', 'car_model__make').all())
            if active_vehicle.vin_number and not vin_query:
                vin_query = active_vehicle.vin_number

    # Cross-Reference & Advanced Parts Search
    if q:
        products_list = find_parts_with_cross_reference(q, base_queryset=products_qs)
    else:
        products_list = list(products_qs)

    # Vehicle fitment filters
    car_make_id = request.GET.get("make", "").strip()
    car_model_id = request.GET.get("carmodel", "").strip()
    
    # Auto-fill from active vehicle if present and not manually overridden
    if active_vehicle and active_vehicle.car_model and not car_model_id and not car_make_id:
        car_model_id = str(active_vehicle.car_model.id)
        car_make_id = str(active_vehicle.car_model.make_id)

    active_make = None
    active_model = None

    if car_model_id and car_model_id.isdigit():
        try:
            active_model = CarModel.objects.select_related("make").get(id=int(car_model_id))
            products_list = [p for p in products_list if active_model in p.compatibilities.all() or active_model.name.lower() in (p.vehicle_application or '').lower()]
            car_make_id = str(active_model.make_id)
            active_make = active_model.make
        except CarModel.DoesNotExist:
            car_model_id = ""

    if car_make_id and not active_model and car_make_id.isdigit():
        try:
            active_make = CarMake.objects.get(id=int(car_make_id))
            products_list = [p for p in products_list if any(cm.make_id == active_make.id for cm in p.compatibilities.all())]
        except CarMake.DoesNotExist:
            car_make_id = ""

    # Live Fitment Verification per Product if VIN or Model specified
    target_mid = active_model.id if active_model else None
    for p in products_list:
        if vin_query or target_mid:
            fit_res = verify_product_fitment(p, vin_or_query=vin_query, car_model_id=target_mid)
            p.fit_status = fit_res.get("status")
            p.fits_vehicle = fit_res.get("fits")
            p.fit_badge_text = fit_res.get("badge_text")
            p.fit_detail = fit_res.get("detail")
            p.fit_icon = fit_res.get("icon")
        else:
            p.fit_status = None
            p.fits_vehicle = None
            p.fit_badge_text = None
            p.fit_detail = None
            p.fit_icon = None

    car_makes = CarMake.objects.prefetch_related('models').order_by('name')
    all_customers = Customer.objects.all().order_by('name')

    return render(request, "sales/pos.html", {
        "products": products_list,
        "cart_count": cart_count,
        "cart_items": cart_items,
        "car_makes": car_makes,
        "filter_make": car_make_id,
        "filter_model": car_model_id,
        "active_make": active_make,
        "active_model": active_model,
        "vin_query": vin_query,
        "all_customers": all_customers,
        "active_customer": active_customer,
        "customer_vehicles": customer_vehicles,
        "active_vehicle": active_vehicle,
        "search_query": q,
    })


@login_required
def add_to_cart(request, product_id):
    """Add one unit of the given product to the session cart and redirect to cart."""
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product, defaults={'quantity': 1})
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect("cart")


@login_required
def remove_from_cart(request, product_id):
    Cart.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect("cart")


@login_required
def cart_view(request):
    """Display cart contents and handle checkout for multiple items with Ethiopian fiscal invoice fields."""
    from .models import Sale, SaleItem, Customer
    from reports.models import BusinessProfile
    from django.utils import timezone

    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    products = []
    for item in cart_items:
        prod = item.product
        qty = item.quantity
        override = item.price_override
        products.append((prod, qty, override))

    errors = []
    if request.method == "POST":
        # update quantities and prices from form
        for item in cart_items:
            prod = item.product
            raw_qty = request.POST.get(f"qty_{prod.id}", "0") or "0"
            try:
                q = int(raw_qty)
            except (ValueError, TypeError):
                q = 0
            raw_price = request.POST.get(f"price_{prod.id}", "").strip()
            price_override = None
            if raw_price:
                try:
                    price_override = float(raw_price)
                except ValueError:
                    price_override = None
            if q > 0:
                if q > prod.quantity:
                    errors.append(f"Insufficient stock for {prod.name}: requested {q}, only {prod.quantity} available.")
                else:
                    item.quantity = q
                    item.price_override = price_override
                    item.save()
            else:
                item.delete()

        if errors:
            customers = Customer.objects.all().order_by('name')
            return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale})

        # no items
        if not Cart.objects.filter(user=request.user).exists():
            errors.append("No items in cart.")
            customers = Customer.objects.all().order_by('name')
            return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale})

        # handle buyer information
        customer_type = request.POST.get('customer_type', 'existing')
        existing_cust_id = request.POST.get('customer_id', '').strip()
        customer_name = request.POST.get('customer_name', '').strip()
        
        # New or explicit buyer fields
        new_name = request.POST.get('new_name', '').strip()
        company_name = request.POST.get('company_name', '').strip()
        tin_number = request.POST.get('tin_number', '').strip()
        vat_number = request.POST.get('vat_number', '').strip()
        phone = request.POST.get('phone', '').strip() or request.POST.get('new_phone', '').strip()
        address = request.POST.get('address', '').strip()

        # Payment and Fiscal details
        payment = request.POST.get('payment_method', 'CASH')
        fs_number_input = request.POST.get('fs_number', '').strip()
        payment_ref = request.POST.get('payment_reference', '').strip().upper()
        selected_vehicle_id = request.POST.get('vehicle_id', '').strip()
        new_plate = request.POST.get('new_vehicle_plate', '').strip().upper()
        new_veh_desc = request.POST.get('new_vehicle_desc', '').strip()

        cust = None
        if customer_type == 'existing':
            if existing_cust_id and existing_cust_id.isdigit():
                cust = Customer.objects.filter(id=int(existing_cust_id)).first()
            if not cust and customer_name:
                cust = Customer.objects.filter(Q(name__iexact=customer_name) | Q(company_name__iexact=customer_name)).first()
            if cust:
                # Update buyer tax/company info if provided and empty
                if company_name and not cust.company_name:
                    cust.company_name = company_name
                if tin_number and not cust.tin_number:
                    cust.tin_number = tin_number
                if vat_number and not cust.vat_number:
                    cust.vat_number = vat_number
                if phone and not cust.phone:
                    cust.phone = phone
                if address and not cust.address:
                    cust.address = address
                cust.save()

        if not cust and (new_name or company_name or customer_name):
            primary_name = new_name or company_name or customer_name or "Walk-in Buyer"
            cust = Customer.objects.create(
                name=primary_name,
                company_name=company_name,
                tin_number=tin_number,
                vat_number=vat_number,
                phone=phone,
                address=address,
            )

        # Vehicle association
        matched_vehicle = None
        if selected_vehicle_id.isdigit():
            matched_vehicle = CustomerVehicle.objects.filter(id=int(selected_vehicle_id)).first()
        elif new_plate and cust:
            matched_vehicle = CustomerVehicle.objects.create(
                customer=cust,
                plate_number=new_plate,
                custom_name=new_veh_desc or "Registered Vehicle",
            )

        # create sale
        with transaction.atomic():
            sales_receipt = request.FILES.get('sales_receipt')
            sale = Sale.objects.create(
                payment_method=payment,
                customer=cust,
                vehicle=matched_vehicle,
                cashier=request.user,
                receipt_file=sales_receipt,
                receipt_reference=fs_number_input,
                document_date=timezone.localdate(),
            )
            total = 0
            for item in Cart.objects.filter(user=request.user).select_related('product'):
                prod = item.product
                qty = item.quantity
                # determine unit price: POST > override > default
                price_override = request.POST.get(f"price_{prod.id}", "").strip()
                if price_override:
                    try:
                        unit_price = float(price_override)
                    except ValueError:
                        unit_price = item.price_override or prod.selling_price
                elif item.price_override:
                    unit_price = item.price_override
                else:
                    unit_price = prod.selling_price

                SaleItem.objects.create(
                    sale=sale,
                    product=prod,
                    quantity=qty,
                    price=unit_price,
                    cost_price=prod.cost_price,
                )
                total += qty * unit_price

            # Standard 15% VAT calculation in Ethiopia
            subtotal = round(total / 1.15, 2)
            vat_val = round(total - subtotal, 2)

            sale.total_amount = total
            sale.subtotal_amount = subtotal
            sale.tax_amount = vat_val
            sale.fs_number = fs_number_input if fs_number_input else f"FS-{sale.id:06d}"
            sale.save()
            sale.award_loyalty_points()

            # Record or reconcile Mobile Money / Bank Transfer payment
            if payment_ref:
                existing_pt = PaymentTransaction.objects.filter(transaction_reference=payment_ref).first()
                if existing_pt:
                    existing_pt.sale = sale
                    existing_pt.status = "RECONCILED"
                    existing_pt.save()
                else:
                    prov_choice = "TELEBIRR" if payment == "TELEBIRR" else ("CBE_BIRR" if payment == "CBE_BIRR" else "CBE_TRANSFER")
                    PaymentTransaction.objects.create(
                        provider=prov_choice,
                        transaction_reference=payment_ref,
                        amount=total,
                        payer_phone=cust.phone if cust else "",
                        payer_name=cust.name if cust else "",
                        sale=sale,
                        status="RECONCILED",
                        verified_by=request.user,
                        notes=f"Auto-reconciled during checkout for FS #{sale.fs_number}",
                    )

        # clear cart
        Cart.objects.filter(user=request.user).delete()
        return redirect("invoice", sale.id)

    customers = Customer.objects.all().order_by('name')
    return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale})


@login_required
def pos_single(request, product_id):
    """Display a single-product form that allows adding to cart."""
    product = get_object_or_404(Product, id=product_id)
    errors = []
    qty = 0
    unit_price = product.selling_price

    if request.method == 'POST':
        raw_qty = request.POST.get('qty', '0') or '0'
        try:
            qty = int(raw_qty)
        except (ValueError, TypeError):
            qty = 0
        if qty <= 0:
            errors.append('Quantity must be greater than zero.')
        elif qty > product.quantity:
            errors.append(f'Insufficient stock for {product.name}.')

        price_override = request.POST.get('price', '').strip()
        if price_override:
            try:
                unit_price = float(price_override)
            except ValueError:
                unit_price = product.selling_price

        if not errors:
            cart_item, created = Cart.objects.get_or_create(user=request.user, product=product, defaults={'quantity': qty, 'price_override': unit_price if price_override else None})
            if not created:
                cart_item.quantity = qty
                cart_item.price_override = unit_price if price_override else None
                cart_item.save()
            return redirect('cart')

    return render(
        request,
        'sales/pos_single.html',
        {
            'product': product,
            'errors': errors,
            'qty': qty,
            'unit_price': unit_price,
        },
    )


@login_required
def scan_barcode_api(request):
    """
    High-speed Barcode & SKU Scanner API for POS handheld guns and search inputs.
    Looks up products by SKU, OEM part number, or alternate OEM numbers.
    Automatically increments or adds the item to the user's active Cart.
    """
    code = (request.GET.get("code") or request.POST.get("code") or "").strip()
    if not code:
        return JsonResponse({"success": False, "error": "Scan code empty"}, status=400)

    # 1. Search by SKU, Part Number (OEM), or Alternate OEM Numbers
    product = (
        Product.objects.filter(
            Q(sku__iexact=code)
            | Q(part_number__iexact=code)
            | Q(alternate_numbers__icontains=code)
        )
        .first()
    )

    if not product:
        return JsonResponse({
            "success": False,
            "error": f"No spare part matched barcode / SKU: '{code}'",
            "code": code,
        }, status=404)

    # Check stock
    if product.quantity <= 0:
        return JsonResponse({
            "success": False,
            "error": f"Out of stock: {product.name} (Part #{product.part_number}) has 0 inventory.",
            "product": {
                "id": product.id,
                "name": product.name,
                "part_number": product.part_number,
                "sku": product.sku,
                "quantity": product.quantity,
            }
        }, status=400)

    # Add or increment item in Cart
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={"quantity": 1}
    )
    if not created:
        if cart_item.quantity < product.quantity:
            cart_item.quantity += 1
            cart_item.save()
        else:
            return JsonResponse({
                "success": False,
                "error": f"Cannot add more: Cart already has max available stock ({product.quantity} {product.uom_short}).",
                "product_name": product.name,
            }, status=400)

    new_cart_count = sum(item.quantity for item in Cart.objects.filter(user=request.user))

    return JsonResponse({
        "success": True,
        "message": f"✓ {product.name} added to cart (Qty: {cart_item.quantity})",
        "cart_count": new_cart_count,
        "product": {
            "id": product.id,
            "name": product.name,
            "part_number": product.part_number,
            "sku": product.sku,
            "brand": product.brand,
            "selling_price": product.selling_price,
            "unit": product.uom_short,
            "unit_amharic": product.uom_amharic,
            "quantity_available": product.quantity,
            "cart_quantity": cart_item.quantity,
        }
    })


@login_required
def customer_list(request):
    search = request.GET.get("q", "").strip()
    customers = Customer.objects.all()
    if search:
        customers = customers.filter(
            Q(name__icontains=search)
            | Q(company_name__icontains=search)
            | Q(tin_number__icontains=search)
            | Q(vat_number__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )
    page = Paginator(customers.order_by("name", "id"), 25).get_page(request.GET.get("page"))
    return render(request, "sales/customer_list.html", {
        "customers": page,
        "page": page,
        "search": search,
    })


@login_required
def customer_detail(request, pk):
    from .models import Customer, LoyaltyTransaction
    cust = get_object_or_404(Customer, id=pk)
    sales = Sale.objects.filter(customer=cust).prefetch_related('items', 'vehicle').order_by('-date')
    transactions = LoyaltyTransaction.objects.filter(customer=cust).order_by('-date')
    vehicles = cust.vehicles.select_related('car_model', 'car_model__make').all()
    car_makes = CarMake.objects.prefetch_related('models').order_by('name')
    return render(request, "sales/customer_detail.html", {
        "customer": cust,
        "sales": sales,
        "transactions": transactions,
        "vehicles": vehicles,
        "car_makes": car_makes,
    })


@login_required
def customer_add_vehicle(request, pk):
    """Register a new vehicle into regular customer or garage fleet."""
    cust = get_object_or_404(Customer, id=pk)
    if request.method == "POST":
        plate = request.POST.get("plate_number", "").strip().upper()
        vin = request.POST.get("vin_number", "").strip().upper()
        custom_name = request.POST.get("custom_name", "").strip()
        model_id = request.POST.get("car_model_id", "").strip()
        engine = request.POST.get("engine", "").strip()
        year_raw = request.POST.get("manufacture_year", "").strip()
        notes = request.POST.get("notes", "").strip()

        year = int(year_raw) if year_raw.isdigit() else None
        car_model = None
        if model_id.isdigit():
            car_model = CarModel.objects.filter(id=int(model_id)).first()

        CustomerVehicle.objects.create(
            customer=cust,
            car_model=car_model,
            custom_name=custom_name,
            plate_number=plate,
            vin_number=vin,
            engine=engine,
            manufacture_year=year,
            notes=notes,
        )
        messages.success(request, f"✓ Vehicle '{plate or custom_name or 'New Vehicle'}' registered to {cust.display_name} fleet!")
    return redirect("customer_detail", pk=cust.id)


@login_required
def customer_delete_vehicle(request, pk, vehicle_id):
    """Remove a vehicle from customer fleet."""
    cust = get_object_or_404(Customer, id=pk)
    veh = get_object_or_404(CustomerVehicle, id=vehicle_id, customer=cust)
    veh.delete()
    messages.success(request, "Vehicle removed from customer profile.")
    return redirect("customer_detail", pk=cust.id)


@login_required
def customer_vehicles_api(request, pk):
    """Returns JSON list of vehicles registered to a customer."""
    cust = get_object_or_404(Customer, id=pk)
    vehicles = cust.vehicles.select_related('car_model', 'car_model__make').all()
    data = []
    for v in vehicles:
        data.append({
            "id": v.id,
            "plate_number": v.plate_number,
            "display_title": v.display_title,
            "vin_number": v.vin_number,
            "model_id": v.car_model.id if v.car_model else None,
            "make_name": v.car_model.make.name if v.car_model else "",
            "model_name": v.car_model.name if v.car_model else v.custom_name,
            "engine": v.engine,
            "year": v.manufacture_year,
        })
    return JsonResponse({"success": True, "vehicles": data})


@login_required
def invoice_view(request, sale_id):
    from reports.models import BusinessProfile
    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'cashier').prefetch_related('items__product'),
        id=sale_id
    )
    profile = BusinessProfile.get_profile()
    return render(request, "sales/invoice.html", {
        "sale": sale,
        "profile": profile,
    })
from inventory.models import Product, StockMovement
from .models import Cart, Sale, SaleItem, Customer

@login_required
def pending_orders(request):
    from django.core.mail import send_mail
    from django.conf import settings
    
    if request.method == 'POST':
        sale_id = request.POST.get('sale_id')
        action = request.POST.get('action')
        sale = get_object_or_404(Sale, id=sale_id, status='PENDING')
        
        if action == 'approve':
            with transaction.atomic():
                sale.status = 'APPROVED'
                sale.save()
                
                # Send email to customer
                if sale.customer and sale.customer.email:
                    subject = f"Order #{sale.id} Approved - {settings.APP_NAME}"
                    message = f"""
Dear {sale.customer.name},

Your order #{sale.id} has been approved and is now being processed.

Order Details:
- Total Amount: ${sale.total_amount:.2f}
- Payment Method: {sale.payment_method}

Estimated arrival time: 3-5 business days.

Thank you for shopping with us!

{settings.APP_NAME}
"""
                    try:
                        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [sale.customer.email])
                    except Exception as e:
                        messages.warning(request, f"Order approved but email failed to send: {e}")
                
                messages.success(request, f"Order #{sale.id} approved and inventory updated.")
        
        elif action == 'cancel':
            with transaction.atomic():
                for item in sale.items.all():
                    prod = item.product
                    prod.refresh_from_db(fields=["quantity"])
                    prod.quantity = (prod.quantity or 0) + item.quantity
                    prod._bypass_adjustment_signal = True
                    prod.save(update_fields=["quantity"])
                    
                    # Log stock restoration
                    StockMovement.objects.create(
                        product=prod,
                        quantity=item.quantity,
                        movement_type="adjustment",
                        reference=f"Cancelled Order Sale#{sale.id} recovery",
                    )
                sale.status = 'CANCELLED'
                sale.save()
            messages.success(request, f"Order #{sale.id} cancelled and stock returned to inventory.")
        
        return redirect('pending_orders')
    
    pending_sales = Sale.objects.filter(status='PENDING').prefetch_related('items__product', 'customer').order_by('-date')
    return render(request, 'sales/pending_orders.html', {'pending_sales': pending_sales})


@login_required
def sales_report(request):
    sales = Sale.objects.prefetch_related("items").order_by("-date")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    if date_from:
        sales = sales.filter(date__date__gte=date_from)
    if date_to:
        sales = sales.filter(date__date__lte=date_to)
    total_sales = sum(s.total_amount for s in sales)
    total_profit = sum(s.profit() for s in sales)
    return render(
        request,
        "sales/report.html",
        {
            "sales": sales,
            "total_sales": total_sales,
            "total_profit": total_profit,
            "date_from": date_from,
            "date_to": date_to,
        }
    )


@login_required
def invoice_pdf(request, sale_id):
    from reports.models import BusinessProfile
    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'cashier').prefetch_related('items__product'),
        id=sale_id
    )
    profile = BusinessProfile.get_profile()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="Tax_Invoice_{sale.get_fs_number()}_{sale.id}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin = 40
    content_width = width - (margin * 2)

    def draw_header_and_boxes(canvas_obj):
        y = height - 36
        # Top Header - Seller Official Information
        canvas_obj.setFillColorRGB(0.06, 0.09, 0.16) # Dark slate
        canvas_obj.setFont("Helvetica-Bold", 16)
        shop_title = profile.trade_name or profile.name or "CAR SPARE PARTS SHOP"
        canvas_obj.drawString(margin, y, shop_title.upper())

        # Document Title on Top Right
        canvas_obj.setFillColorRGB(0.08, 0.45, 0.42) # Teal / Emerald
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawRightString(width - margin, y, "TAX INVOICE / FISCAL RECEIPT")
        y -= 14

        # Seller Address and Contact
        canvas_obj.setFillColorRGB(0.3, 0.35, 0.4)
        canvas_obj.setFont("Helvetica", 8.5)
        addr = profile.address or "Woreda 07 Teklehaymanot, Addis Hope Building, AHG-022, Addis Ababa, Ethiopia"
        canvas_obj.drawString(margin, y, f"Address: {addr}")
        canvas_obj.drawRightString(width - margin, y, "ORIGINAL CUSTOMER COPY")
        y -= 13

        # Seller Mandatory TIN and VAT Registration Numbers
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.setFillColorRGB(0.1, 0.15, 0.25)
        seller_tax_str = f"Seller TIN: {profile.tin_number or '0081095335'}   |   VAT Reg No: {profile.vat_number or '42178020821'}"
        canvas_obj.drawString(margin, y, seller_tax_str)

        phone_email = []
        if profile.phone:
            phone_email.append(f"Tel: {profile.phone}")
        if profile.email:
            phone_email.append(f"Email: {profile.email}")
        if phone_email:
            canvas_obj.setFont("Helvetica", 8.5)
            canvas_obj.drawRightString(width - margin, y, " | ".join(phone_email))
        y -= 10

        # Separator line
        canvas_obj.setStrokeColorRGB(0.8, 0.84, 0.88)
        canvas_obj.setLineWidth(1)
        canvas_obj.line(margin, y, width - margin, y)
        y -= 12

        # Two Box Information Panels
        # Left Box: Buyer / Customer Info (width: 250)
        box_y = y - 82
        box_h = 82
        left_box_w = 250
        right_box_x = margin + left_box_w + 15
        right_box_w = content_width - left_box_w - 15

        # Draw Left Box Background & Border
        canvas_obj.setFillColorRGB(0.97, 0.98, 0.99)
        canvas_obj.setStrokeColorRGB(0.85, 0.88, 0.92)
        canvas_obj.rect(margin, box_y, left_box_w, box_h, fill=1, stroke=1)

        # Left Box Header
        canvas_obj.setFillColorRGB(0.08, 0.45, 0.42)
        canvas_obj.rect(margin, box_y + box_h - 18, left_box_w, 18, fill=1, stroke=0)
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 8, box_y + box_h - 13, "BILLED TO (BUYER DETAILS)")

        # Left Box Content
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)
        by = box_y + box_h - 30
        c_name = "Walk-in Retail Buyer"
        c_comp = ""
        c_tin = "Unregistered / Consumer"
        c_phone = "—"
        c_addr = ""

        if sale.customer:
            c_comp = sale.customer.company_name or ""
            c_name = sale.customer.name or c_comp or "Customer"
            c_tin = sale.customer.tin_number or "Unregistered / Consumer"
            c_phone = sale.customer.phone or "—"
            c_addr = sale.customer.address or ""

        if c_comp:
            canvas_obj.setFont("Helvetica-Bold", 9)
            canvas_obj.drawString(margin + 8, by, c_comp[:36])
            by -= 12
            canvas_obj.setFont("Helvetica", 8.5)
            canvas_obj.drawString(margin + 8, by, f"Attn: {c_name[:34]}")
        else:
            canvas_obj.setFont("Helvetica-Bold", 9)
            canvas_obj.drawString(margin + 8, by, c_name[:36])

        by -= 13
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 8, by, "Buyer TIN:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(margin + 62, by, c_tin[:28])

        by -= 12
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 8, by, "Phone:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(margin + 62, by, c_phone[:28])

        # Right Box: Invoice & Fiscal Reference
        canvas_obj.setFillColorRGB(0.97, 0.98, 0.99)
        canvas_obj.rect(right_box_x, box_y, right_box_w, box_h, fill=1, stroke=1)

        # Right Box Header
        canvas_obj.setFillColorRGB(0.15, 0.23, 0.36)
        canvas_obj.rect(right_box_x, box_y + box_h - 18, right_box_w, 18, fill=1, stroke=0)
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, box_y + box_h - 13, "FISCAL RECEIPT & TRANSACTION META")

        # Right Box Content
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)
        ry = box_y + box_h - 30

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, ry, "Invoice No:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(right_box_x + 80, ry, f"INV-{sale.id:06d}")

        ry -= 12
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, ry, "Fiscal Receipt #:")
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.setFillColorRGB(0.08, 0.45, 0.42)
        canvas_obj.drawString(right_box_x + 80, ry, sale.get_fs_number())
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)

        ry -= 12
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, ry, "Date & Time:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(right_box_x + 80, ry, sale.date.strftime("%d/%m/%Y  %I:%M %p"))

        ry -= 12
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, ry, "Payment Mode:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(right_box_x + 80, ry, sale.get_payment_method_display()[:24])

        ry -= 12
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 8, ry, "Cashier / Staff:")
        canvas_obj.setFont("Helvetica", 8.5)
        staff = sale.cashier.get_full_name() or sale.cashier.username if sale.cashier else "Counter Admin"
        canvas_obj.drawString(right_box_x + 80, ry, staff[:24])

        return box_y - 18

    def draw_table_header(canvas_obj, curr_y):
        # Table Header Row
        canvas_obj.setFillColorRGB(0.92, 0.94, 0.97)
        canvas_obj.rect(margin, curr_y - 4, content_width, 18, fill=1, stroke=0)
        canvas_obj.setStrokeColorRGB(0.75, 0.8, 0.86)
        canvas_obj.line(margin, curr_y - 4, width - margin, curr_y - 4)
        canvas_obj.line(margin, curr_y + 14, width - margin, curr_y + 14)

        canvas_obj.setFillColorRGB(0.1, 0.15, 0.25)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawString(margin + 6, curr_y + 1, "#")
        canvas_obj.drawString(margin + 28, curr_y + 1, "PART NUMBER / SKU")
        canvas_obj.drawString(margin + 140, curr_y + 1, "SPARE PART DESCRIPTION")
        canvas_obj.drawString(width - margin - 190, curr_y + 1, "QTY")
        canvas_obj.drawRightString(width - margin - 85, curr_y + 1, "UNIT PRICE (ETB)")
        canvas_obj.drawRightString(width - margin - 8, curr_y + 1, "TOTAL (ETB)")
        return curr_y - 18

    # Start drawing first page
    curr_y = draw_header_and_boxes(p)
    curr_y = draw_table_header(p, curr_y)

    # Line Items
    items = list(sale.items.all())
    for idx, item in enumerate(items, 1):
        if curr_y < 120:
            p.showPage()
            curr_y = height - 40
            curr_y = draw_table_header(p, curr_y)

        line_total = item.quantity * item.price
        p.setFont("Helvetica", 8.5)
        p.setFillColorRGB(0.35, 0.4, 0.45)
        p.drawString(margin + 6, curr_y, str(idx))

        p.setFont("Helvetica-Bold", 8.5)
        p.setFillColorRGB(0.1, 0.15, 0.25)
        part_no = (item.product.part_number or "—")[:18]
        p.drawString(margin + 28, curr_y, part_no)

        p.setFont("Helvetica", 8.5)
        p.drawString(margin + 140, curr_y, item.product.name[:38])

        p.drawString(width - margin - 185, curr_y, str(item.quantity))
        p.drawRightString(width - margin - 85, curr_y, f"{item.price:,.2f}")
        p.setFont("Helvetica-Bold", 8.5)
        p.drawRightString(width - margin - 8, curr_y, f"{line_total:,.2f}")

        # Light divider line
        curr_y -= 6
        p.setStrokeColorRGB(0.92, 0.94, 0.96)
        p.setLineWidth(0.5)
        p.line(margin, curr_y, width - margin, curr_y)
        curr_y -= 12

    # Totals Section Box
    if curr_y < 130:
        p.showPage()
        curr_y = height - 60

    curr_y -= 6
    p.setStrokeColorRGB(0.8, 0.84, 0.88)
    p.setLineWidth(1)
    p.line(margin, curr_y, width - margin, curr_y)
    curr_y -= 14

    # Summary calculation table (right aligned)
    tot_box_w = 230
    tot_box_x = width - margin - tot_box_w
    
    # Subtotal
    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.3, 0.35, 0.4)
    p.drawString(tot_box_x, curr_y, "Taxable Subtotal (Excl. VAT):")
    p.drawRightString(width - margin - 8, curr_y, f"ETB {sale.calculated_subtotal:,.2f}")
    curr_y -= 14

    # VAT (15%)
    p.drawString(tot_box_x, curr_y, "Value Added Tax (15% VAT):")
    p.drawRightString(width - margin - 8, curr_y, f"ETB {sale.calculated_vat:,.2f}")
    curr_y -= 14

    # Grand Total Banner
    p.setFillColorRGB(0.08, 0.45, 0.42)
    p.rect(tot_box_x - 6, curr_y - 6, tot_box_w + 6, 22, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10.5)
    p.drawString(tot_box_x, curr_y + 1, "GRAND TOTAL (ETB):")
    p.drawRightString(width - margin - 8, curr_y + 1, f"ETB {sale.total_amount:,.2f}")

    # Official Footnote & Legal Tax Notice
    p.setFont("Helvetica-Bold", 8)
    p.setFillColorRGB(0.2, 0.25, 0.3)
    p.drawString(margin, 46, "Official Ethiopian Fiscal Tax Invoice - Approved Format")
    p.setFont("Helvetica", 7.5)
    p.setFillColorRGB(0.45, 0.5, 0.55)
    p.drawString(margin, 35, f"Seller TIN: {profile.tin_number or '0081095335'} | VAT No: {profile.vat_number or '42178020821'} | Address: {profile.address}")
    p.drawString(margin, 24, "Thank you for choosing our car spare parts shop! Goods sold are backed by standard warranty against factory defects.")

    p.showPage()
    p.save()
    return response
