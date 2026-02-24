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
from .models import Sale, SaleItem

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
    products = Product.objects.all()
    q = request.GET.get("q", "").strip()
    if q:
        products = products.filter(
            Q(name__icontains=q)
            | Q(part_number__icontains=q)
            | Q(brand__icontains=q)
            | Q(compatibilities__name__icontains=q)
            | Q(compatibilities__make__name__icontains=q)
        ).distinct()

    if request.method == "POST":
        # Validate stock before processing
        cart = []
        errors = []
        for product in products:
            raw_qty = request.POST.get(f"qty_{product.id}", 0) or 0
            try:
                qty = int(raw_qty)
            except (ValueError, TypeError):
                qty = 0
            if qty > 0:
                if qty > product.quantity:
                    errors.append(f"Insufficient stock for {product.name}: requested {qty}, only {product.quantity} available.")
                else:
                    cart.append((product, qty))

        if errors:
            return render(request, "sales/pos.html", {
                "products": products,
                "errors": errors,
            })

        # determine price type (retail/wholesale) from submitted form (default retail)
        price_type = request.POST.get('price_type', request.GET.get('price_type', 'retail'))

        with transaction.atomic():
            sale = Sale.objects.create(payment_method="CASH")
            total = 0

            for product, qty in cart:
                # choose unit price according to selected price type
                if price_type == 'wholesale':
                    unit_price = product.wholesale_price or product.selling_price
                else:
                    unit_price = product.selling_price

                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty,
                    price=unit_price,
                    cost_price=product.cost_price,
                )

                total += qty * unit_price

            sale.total_amount = total
            sale.save()

        return redirect("invoice", sale.id)

    return render(request, "sales/pos.html", {"products": products})


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
