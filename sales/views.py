from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from expenses.models import Expense
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required



from inventory.models import Product
from .models import Sale, SaleItem, Customer

@login_required
@permission_required('sales.add_sale', raise_exception=True)
def create_sale(request):
    ...


@login_required
def full_business_report(request):
    sales = Sale.objects.all()
    expenses = Expense.objects.all()

    total_revenue = sum(s.total_amount for s in sales)
    total_profit = sum(s.profit() for s in sales)
    total_expenses = sum(e.amount for e in expenses)

    net_profit = total_profit - total_expenses

    return render(
        request,
        "sales/full_report.html",
        {
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_expenses": total_expenses,
            "net_profit": net_profit,
        }
    )


@login_required
def pos_view(request):
    # list products only; pricing and sale handled on separate page or via cart
    products = Product.objects.all()
    cart = request.session.get("cart", {})
    cart_prices = request.session.get("cart_prices", {})
    cart_count = sum(cart.values())

    # build cart items for preview
    cart_items = []
    for pid, qty in cart.items():
        try:
            prod = Product.objects.get(id=pid)
            override = cart_prices.get(str(pid))
            cart_items.append((prod, qty, override))
        except Product.DoesNotExist:
            pass

    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(part_number__icontains=q)
            | Q(brand__icontains=q)
            | Q(compatibilities__name__icontains=q)
            | Q(compatibilities__make__name__icontains=q)
            | Q(compatibilities__chassis_prefixes__icontains=q)
        ).distinct()
    return render(request, "sales/pos.html", {"products": products, "cart_count": cart_count, "cart_items": cart_items})


@login_required
def add_to_cart(request, product_id):
    """Add one unit of the given product to the session cart and redirect to cart."""
    cart = request.session.get("cart", {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session["cart"] = cart
    return redirect("cart")


@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    cart.pop(str(product_id), None)
    request.session["cart"] = cart
    return redirect("cart")


@login_required
def cart_view(request):
    """Display cart contents and handle checkout for multiple items."""
    from .models import Sale, SaleItem, Customer

    cart = request.session.get("cart", {})
    prices = request.session.get("cart_prices", {})
    products = []
    for pid, qty in list(cart.items()):
        try:
            prod = Product.objects.get(id=pid)
            override = prices.get(str(pid))
            products.append((prod, qty, override))
        except Product.DoesNotExist:
            cart.pop(pid, None)
    request.session["cart"] = cart

    errors = []
    if request.method == "POST":
        # update quantities from form
        new_cart = {}
        for prod, oldqty, override in products:
            raw = request.POST.get(f"qty_{prod.id}", "0") or "0"
            try:
                q = int(raw)
            except (ValueError, TypeError):
                q = 0
            if q > 0:
                if q > prod.quantity:
                    errors.append(f"Insufficient stock for {prod.name}: requested {q}, only {prod.quantity} available.")
                else:
                    new_cart[str(prod.id)] = q
        cart = new_cart
        request.session["cart"] = cart

        if errors:
            customers = Customer.objects.all()
            prices = request.session.get("cart_prices", {})
            return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale, "prices": prices})

        # no items
        if not cart:
            errors.append("No items in cart.")
            customers = Customer.objects.all()
            prices = request.session.get("cart_prices", {})
            return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale, "prices": prices})

        # handle customer and payment similar to pos_single
        customer_type = request.POST.get('customer_type', 'existing')
        customer_name = request.POST.get('customer_name', '').strip()
        new_name = request.POST.get('new_name', '').strip()
        new_phone = request.POST.get('new_phone', '').strip()
        payment = request.POST.get('payment_method', 'CASH')

        cust = None
        if customer_type == 'new' and new_name:
            cust = Customer.objects.create(name=new_name, phone=new_phone)
        elif customer_type == 'existing' and customer_name:
            cust, _ = Customer.objects.get_or_create(name=customer_name)

        # create sale
        with transaction.atomic():
            sale = Sale.objects.create(payment_method=payment, customer=cust)
            total = 0
            for prod, qty, override in products:
                if str(prod.id) not in cart:
                    continue
                qty = cart[str(prod.id)]
                # determine unit price: POST > session override > default
                price_override = request.POST.get(f"price_{prod.id}", "").strip()
                if price_override:
                    try:
                        unit_price = float(price_override)
                    except ValueError:
                        unit_price = 0
                elif override is not None:
                    unit_price = override
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

            sale.total_amount = total
            sale.save()
        # clear cart and prices
        request.session["cart"] = {}
        request.session["cart_prices"] = {}
        return redirect("invoice", sale.id)

    customers = Customer.objects.all()
    prices = request.session.get("cart_prices", {})
    return render(request, "sales/cart.html", {"products": products, "errors": errors, "customers": customers, "Sale": Sale, "prices": prices})


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
            cart = request.session.get('cart', {})
            cart[str(product.id)] = qty
            request.session['cart'] = cart
            # store override price
            prices = request.session.get('cart_prices', {})
            if price_override:
                prices[str(product.id)] = unit_price
            request.session['cart_prices'] = prices
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
def customer_list(request):
    from .models import Customer
    customers = Customer.objects.all()
    return render(request, "sales/customer_list.html", {"customers": customers})


@login_required
def customer_detail(request, pk):
    from .models import Customer
    cust = get_object_or_404(Customer, id=pk)
    sales = Sale.objects.filter(customer=cust).prefetch_related('items')
    return render(request, "sales/customer_detail.html", {"customer": cust, "sales": sales})


@login_required
def invoice_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    return render(request, "sales/invoice.html", {"sale": sale})


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
    sale = get_object_or_404(Sale, id=sale_id)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="invoice_{sale.id}.pdf"'
    )

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    # Header - Shop branding
    p.setFont("Helvetica-Bold", 22)
    p.drawString(margin, y, "ERP MY SHOP")
    y -= 8

    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.4, 0.4, 0.45)
    p.drawString(margin, y, "Sales Invoice")
    p.setFillColorRGB(0, 0, 0)
    y -= 35

    # Invoice details box
    p.setFont("Helvetica-Bold", 14)
    p.drawString(margin, y, f"INVOICE #{sale.id}")
    y -= 20

    p.setFont("Helvetica", 10)
    p.drawString(margin, y, f"Date: {sale.date.strftime('%B %d, %Y at %I:%M %p')}")
    y -= 8
    p.drawString(margin, y, f"Payment: {sale.payment_method}")
    y -= 35

    # Table header
    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin, y, "Product")
    p.drawString(350, y, "Qty")
    p.drawString(400, y, "Unit Price")
    p.drawString(480, y, "Total")
    y -= 5
    p.line(margin, y, width - margin, y)
    y -= 15

    # Table rows
    p.setFont("Helvetica", 10)
    for item in sale.items.all():
        line_total = item.quantity * item.price
        p.drawString(margin, y, str(item.product.name)[:45])
        p.drawString(355, y, str(item.quantity))
        p.drawString(400, y, f"{item.price:,.2f}")
        p.drawString(475, y, f"{line_total:,.2f}")
        y -= 18

        if y < 100:
            p.showPage()
            y = height - margin

    y -= 15
    p.line(margin, y, width - margin, y)
    y -= 20

    # Total
    p.setFont("Helvetica-Bold", 12)
    p.drawString(400, y, "TOTAL:")
    p.drawString(475, y, f"{sale.total_amount:,.2f}")
    y -= 40

    # Footer
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5, 0.5, 0.5)
    p.drawString(margin, 40, "Thank you for your business!")
    p.drawString(margin, 28, f"Invoice generated on {sale.date.strftime('%Y-%m-%d')}")

    p.showPage()
    p.save()
    return response
