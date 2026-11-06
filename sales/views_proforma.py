import os
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from inventory.models import Product, Warehouse
from reports.models import BusinessProfile
from .models import Customer, Sale, SaleItem, Proforma, ProformaItem

# Register Amharic TTF font if present on system
AMHARIC_FONT_NAME = "Helvetica"
ETHIOPIC_FONT_PATH = "/usr/share/fonts/truetype/abyssinica/AbyssinicaSIL-Regular.ttf"
if os.path.exists(ETHIOPIC_FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont("Abyssinica", ETHIOPIC_FONT_PATH))
        AMHARIC_FONT_NAME = "Abyssinica"
    except Exception:
        pass


@login_required
def proforma_list(request):
    """List all issued proforma invoices with search and status filters."""
    proformas = Proforma.objects.select_related("customer", "warehouse").prefetch_related("items").order_by("-date")
    
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    
    if q:
        proformas = proformas.filter(
            Q(proforma_number__icontains=q)
            | Q(buyer_name__icontains=q)
            | Q(buyer_company__icontains=q)
            | Q(buyer_tin__icontains=q)
            | Q(items__description__icontains=q)
            | Q(items__part_number__icontains=q)
        ).distinct()

    if status_filter:
        proformas = proformas.filter(status=status_filter)

    return render(request, "sales/proforma_list.html", {
        "proformas": proformas,
        "search_query": q,
        "status_filter": status_filter,
    })


@login_required
def proforma_create(request):
    """
    Interactive Proforma Creator.
    Allows specifying buyer details, picking parts from inventory or typing custom items,
    setting validity days, and generating the official quotation.
    """
    profile = BusinessProfile.get_profile()
    customers = Customer.objects.all().order_by("name")
    products = Product.objects.all().order_by("name")
    warehouses = Warehouse.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        buyer_name = request.POST.get("buyer_name", "").strip()
        buyer_company = request.POST.get("buyer_company", "").strip()
        buyer_tin = request.POST.get("buyer_tin", "").strip()
        buyer_phone = request.POST.get("buyer_phone", "").strip()
        buyer_address = request.POST.get("buyer_address", "").strip()
        customer_id = request.POST.get("customer_id", "").strip()
        warehouse_id = request.POST.get("warehouse_id", "").strip()
        valid_days = int(request.POST.get("valid_days", "15") or 15)
        payment_terms = request.POST.get("payment_terms", "100% Cash / Bank Transfer upon delivery").strip()
        delivery_terms = request.POST.get("delivery_terms", "Ex-store Teklehaymanot, Addis Ababa").strip()
        default_notes = (
            f"All spare parts are genuine quality. Prices include {profile.vat_rate_percent}% VAT."
            if profile.vat_registered else
            "All spare parts are genuine quality. VAT is not applicable."
        )
        notes = request.POST.get("notes", default_notes).strip()

        customer = None
        if customer_id and customer_id.isdigit():
            customer = Customer.objects.filter(id=int(customer_id)).first()

        warehouse = None
        if warehouse_id and warehouse_id.isdigit():
            warehouse = Warehouse.objects.filter(id=int(warehouse_id)).first()

        # Generate unique sequential Proforma Number: PRF-YYYY-XXXXX
        year_str = timezone.now().strftime("%Y")
        count = Proforma.objects.filter(date__year=timezone.now().year).count() + 1
        proforma_num = f"PRF-{year_str}-{count:04d}"

        valid_until_date = timezone.now().date() + timedelta(days=valid_days)

        with transaction.atomic():
            proforma = Proforma.objects.create(
                proforma_number=proforma_num,
                valid_until=valid_until_date,
                customer=customer,
                buyer_name=buyer_name or buyer_company or "Walk-in Client",
                buyer_company=buyer_company,
                buyer_tin=buyer_tin,
                buyer_phone=buyer_phone,
                buyer_address=buyer_address,
                warehouse=warehouse,
                payment_terms=payment_terms,
                delivery_terms=delivery_terms,
                notes=notes,
                created_by=request.user,
                status="SENT",
            )

            # Process line items from POST lists
            item_descriptions = request.POST.getlist("item_description[]")
            item_part_numbers = request.POST.getlist("item_part_number[]")
            item_units = request.POST.getlist("item_unit[]")
            item_qtys = request.POST.getlist("item_qty[]")
            item_prices = request.POST.getlist("item_price[]")
            item_product_ids = request.POST.getlist("item_product_id[]")

            for i in range(len(item_descriptions)):
                desc = item_descriptions[i].strip() if i < len(item_descriptions) else ""
                if not desc:
                    continue
                part_no = item_part_numbers[i].strip() if i < len(item_part_numbers) else ""
                unit_val = item_units[i].strip() if i < len(item_units) else "Pcs"
                try:
                    q_val = float(item_qtys[i]) if i < len(item_qtys) else 1.0
                except (ValueError, TypeError):
                    q_val = 1.0
                try:
                    p_val = float(item_prices[i]) if i < len(item_prices) else 0.0
                except (ValueError, TypeError):
                    p_val = 0.0

                prod_ref = None
                if i < len(item_product_ids) and item_product_ids[i].isdigit():
                    prod_ref = Product.objects.filter(id=int(item_product_ids[i])).first()

                ProformaItem.objects.create(
                    proforma=proforma,
                    product=prod_ref,
                    part_number=part_no,
                    description=desc,
                    unit=unit_val,
                    quantity=q_val,
                    unit_price=p_val,
                )

            proforma.calculate_totals(profile.vat_rate_percent if profile.vat_registered else 0)

        messages.success(request, f"Proforma {proforma.proforma_number} created successfully!")
        return redirect("proforma_detail", pk=proforma.id)

    return render(request, "sales/proforma_form.html", {
        "customers": customers,
        "products": products,
        "warehouses": warehouses,
        "profile": profile,
    })


@login_required
def proforma_detail(request, pk):
    """
    Displays the official printable bilingual Proforma Invoice.
    Guaranteed single-page layout for up to 15 items with print CSS.
    """
    proforma = get_object_or_404(
        Proforma.objects.select_related("customer", "warehouse", "created_by").prefetch_related("items__product"),
        id=pk
    )
    profile = BusinessProfile.get_profile()
    return render(request, "sales/proforma_detail.html", {
        "proforma": proforma,
        "profile": profile,
    })


@login_required
def proforma_pdf(request, pk):
    """
    Generates a crisp Vector PDF of the Proforma Invoice.
    Guaranteed single-page layout for up to 15 items with bilingual headers.
    """
    proforma = get_object_or_404(
        Proforma.objects.select_related("customer", "warehouse", "created_by").prefetch_related("items__product"),
        id=pk
    )
    profile = BusinessProfile.get_profile()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="Proforma_{proforma.proforma_number}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    p.setTitle(f"{settings.APP_NAME} - Proforma {proforma.proforma_number}")
    width, height = A4
    margin = 38
    content_width = width - (margin * 2)

    def draw_proforma_header(canvas_obj):
        y = height - 32
        
        # Document Type Header
        canvas_obj.setFillColorRGB(0.06, 0.45, 0.42) # Deep Teal
        canvas_obj.rect(margin, y - 18, content_width, 22, fill=1, stroke=0)
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont(AMHARIC_FONT_NAME, 12)
        canvas_obj.drawString(margin + 8, y - 13, "PROFORMA INVOICE  /  የዋጋ ማቅረቢያ ፕሮፎርማ")
        canvas_obj.drawRightString(width - margin - 8, y - 13, f"REF: {proforma.proforma_number}")
        y -= 26

        # Shop Official Title & Seller Info
        canvas_obj.setFillColorRGB(0.1, 0.15, 0.2)
        canvas_obj.setFont("Helvetica-Bold", 17)
        shop_title = profile.trade_name or profile.name or "CAR SPARE PARTS SHOP"
        canvas_obj.drawString(margin, y, shop_title.upper())
        y -= 12

        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.setFillColorRGB(0.35, 0.4, 0.45)
        addr = profile.address or "Woreda 07 Teklehaymanot, Addis Hope Building, AHG-022, Addis Ababa, Ethiopia"
        canvas_obj.drawString(margin, y, f"Address: {addr}")
        
        # Phone / Email on right
        contact_txt = []
        if profile.phone: contact_txt.append(f"Tel: {profile.phone}")
        if profile.email: contact_txt.append(f"Email: {profile.email}")
        if contact_txt:
            canvas_obj.drawRightString(width - margin, y, " | ".join(contact_txt))
        y -= 11

        # Seller Tax Numbers
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.setFillColorRGB(0.1, 0.15, 0.2)
        tin_str = f"Seller TIN: {profile.tin_number or '0081095335'}    |    VAT Reg No: {profile.vat_number or '42178020821'}"
        canvas_obj.drawString(margin, y, tin_str)
        y -= 8

        # Line Separator
        canvas_obj.setStrokeColorRGB(0.8, 0.84, 0.88)
        canvas_obj.setLineWidth(1)
        canvas_obj.line(margin, y, width - margin, y)
        y -= 8

        # Dual Information Boxes (Buyer Info Left, Quotation Meta Right)
        box_y = y - 84
        box_h = 84
        left_box_w = 260
        right_box_x = margin + left_box_w + 12
        right_box_w = content_width - left_box_w - 12

        # Left Box: Buyer
        canvas_obj.setFillColorRGB(0.97, 0.98, 0.99)
        canvas_obj.setStrokeColorRGB(0.85, 0.88, 0.92)
        canvas_obj.rect(margin, box_y, left_box_w, box_h, fill=1, stroke=1)

        canvas_obj.setFillColorRGB(0.12, 0.2, 0.3)
        canvas_obj.rect(margin, box_y + box_h - 15, left_box_w, 15, fill=1, stroke=0)
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(margin + 6, box_y + box_h - 11, "QUOTATION PREPARED FOR (BUYER)")

        by = box_y + box_h - 26
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)
        b_name = proforma.buyer_company or proforma.buyer_name or "Walk-in Client"
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(margin + 6, by, b_name[:36])
        by -= 11

        if proforma.buyer_company and proforma.buyer_name:
            canvas_obj.setFont("Helvetica", 8.5)
            canvas_obj.drawString(margin + 6, by, f"Attn: {proforma.buyer_name[:34]}")
            by -= 10

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 6, by, "Buyer TIN:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(margin + 58, by, proforma.buyer_tin or "Unregistered / Retail")
        by -= 10

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 6, by, "Phone:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(margin + 58, by, proforma.buyer_phone or "—")

        # Right Box: Quotation Meta
        canvas_obj.setFillColorRGB(0.97, 0.98, 0.99)
        canvas_obj.rect(right_box_x, box_y, right_box_w, box_h, fill=1, stroke=1)

        canvas_obj.setFillColorRGB(0.06, 0.45, 0.42)
        canvas_obj.rect(right_box_x, box_y + box_h - 15, right_box_w, 15, fill=1, stroke=0)
        canvas_obj.setFillColorRGB(1, 1, 1)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(right_box_x + 6, box_y + box_h - 11, "PROFORMA VALIDITY & COMMERCIAL META")

        ry = box_y + box_h - 26
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 6, ry, "Date Issued:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(right_box_x + 75, ry, proforma.date.strftime("%d/%m/%Y"))
        ry -= 11

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 6, ry, "Valid Until:")
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.setFillColorRGB(0.8, 0.1, 0.1)
        canvas_obj.drawString(right_box_x + 75, ry, proforma.valid_until.strftime("%d/%m/%Y"))
        canvas_obj.setFillColorRGB(0.1, 0.1, 0.1)
        ry -= 11

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 6, ry, "Payment Terms:")
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.drawString(right_box_x + 75, ry, (proforma.payment_terms or "Cash / Bank Transfer")[:28])
        ry -= 11

        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(right_box_x + 6, ry, "Prepared By:")
        canvas_obj.setFont("Helvetica", 8.5)
        creator = proforma.created_by.get_full_name() or proforma.created_by.username if proforma.created_by else "Sales Admin"
        canvas_obj.drawString(right_box_x + 75, ry, creator[:28])

        return box_y - 12

    def draw_proforma_table_header(canvas_obj, curr_y):
        canvas_obj.setFillColorRGB(0.92, 0.94, 0.97)
        canvas_obj.rect(margin, curr_y - 3, content_width, 16, fill=1, stroke=0)
        canvas_obj.setStrokeColorRGB(0.7, 0.75, 0.82)
        canvas_obj.line(margin, curr_y - 3, width - margin, curr_y - 3)
        canvas_obj.line(margin, curr_y + 13, width - margin, curr_y + 13)

        canvas_obj.setFillColorRGB(0.1, 0.15, 0.25)
        canvas_obj.setFont("Helvetica-Bold", 8.5)
        canvas_obj.drawString(margin + 5, curr_y + 1, "#")
        canvas_obj.drawString(margin + 24, curr_y + 1, "PART NUMBER / OEM")
        canvas_obj.drawString(margin + 125, curr_y + 1, "SPARE PART DESCRIPTION")
        canvas_obj.drawString(width - margin - 175, curr_y + 1, "UNIT")
        canvas_obj.drawString(width - margin - 135, curr_y + 1, "QTY")
        canvas_obj.drawRightString(width - margin - 75, curr_y + 1, "UNIT PRICE (ETB)")
        canvas_obj.drawRightString(width - margin - 6, curr_y + 1, "TOTAL (ETB)")
        return curr_y - 14

    curr_y = draw_proforma_header(p)
    curr_y = draw_proforma_table_header(p, curr_y)

    items = list(proforma.items.all())
    for idx, item in enumerate(items, 1):
        if curr_y < 95:
            p.showPage()
            curr_y = height - 40
            curr_y = draw_proforma_table_header(p, curr_y)

        line_tot = item.quantity * item.unit_price

        p.setFont("Helvetica", 9)
        p.setFillColorRGB(0.4, 0.45, 0.5)
        p.drawString(margin + 5, curr_y, str(idx))

        p.setFont("Helvetica-Bold", 9)
        p.setFillColorRGB(0.1, 0.15, 0.25)
        p.drawString(margin + 24, curr_y, (item.part_number or "—")[:18])

        p.setFont("Helvetica", 9)
        p.drawString(margin + 125, curr_y, item.description[:40])

        p.drawString(width - margin - 175, curr_y, item.unit[:8])
        p.drawString(width - margin - 135, curr_y, str(item.quantity))
        p.drawRightString(width - margin - 75, curr_y, f"{item.unit_price:,.2f}")
        
        p.setFont("Helvetica-Bold", 9)
        p.drawRightString(width - margin - 6, curr_y, f"{line_tot:,.2f}")

        # Light divider line
        curr_y -= 8
        p.setStrokeColorRGB(0.92, 0.94, 0.96)
        p.setLineWidth(0.5)
        p.line(margin, curr_y, width - margin, curr_y)
        curr_y -= 14

    # Summary Section
    if curr_y < 95:
        p.showPage()
        curr_y = height - 50

    curr_y -= 4
    p.setStrokeColorRGB(0.8, 0.84, 0.88)
    p.setLineWidth(1)
    p.line(margin, curr_y, width - margin, curr_y)
    curr_y -= 12

    # Left: Commercial Terms
    p.setFont(AMHARIC_FONT_NAME, 9)
    p.setFillColorRGB(0.2, 0.25, 0.3)
    p.drawString(margin, curr_y, "TERMS & CONDITIONS (የሽያጭ ደንቦች):")
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.4, 0.45, 0.5)
    p.drawString(margin, curr_y - 10, f"• Delivery: {proforma.delivery_terms or 'Ex-store Addis Ababa'}")
    p.drawString(margin, curr_y - 19, f"• Payment: {proforma.payment_terms or 'Cash / Bank Transfer upon delivery'}")
    p.drawString(margin, curr_y - 28, "• Quotation valid for specified period only. Prices inclusive of 15% VAT.")

    # Right: Totals
    tot_box_w = 210
    tot_box_x = width - margin - tot_box_w

    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.3, 0.35, 0.4)
    p.drawString(tot_box_x, curr_y, "Subtotal (Excl. VAT):")
    p.drawRightString(width - margin - 6, curr_y, f"ETB {proforma.calculated_subtotal:,.2f}")
    curr_y -= 12

    p.drawString(tot_box_x, curr_y, "VAT Amount (15%):")
    p.drawRightString(width - margin - 6, curr_y, f"ETB {proforma.calculated_vat:,.2f}")
    curr_y -= 12

    # Grand Total Banner
    p.setFillColorRGB(0.06, 0.45, 0.42)
    p.rect(tot_box_x - 4, curr_y - 4, tot_box_w + 4, 18, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10.5)
    p.drawString(tot_box_x, curr_y + 1, "PROFORMA TOTAL:")
    p.drawRightString(width - margin - 6, curr_y + 1, f"ETB {proforma.total_amount:,.2f}")

    # Footer Notice
    p.setFont("Helvetica-Bold", 8.5)
    p.setFillColorRGB(0.3, 0.35, 0.4)
    p.drawString(margin, 36, "Official Commercial Proforma Quotation - Addis Ababa, Ethiopia")
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.5, 0.55, 0.6)
    p.drawString(margin, 26, f"Seller TIN: {profile.tin_number or '0081095335'} | VAT No: {profile.vat_number or '42178020821'} | Address: {profile.address}")
    p.drawString(margin, 17, "This document is an official quotation, not a final tax invoice. Final VAT sales invoice issued upon payment.")

    p.showPage()
    p.save()
    return response


@login_required
def proforma_convert(request, pk):
    """
    Converts a Proforma quotation into an active Sale, deducting inventory stock
    and redirecting directly to the official sales invoice!
    """
    proforma = get_object_or_404(Proforma, id=pk)
    if proforma.status == "CONVERTED" and proforma.converted_sale:
        messages.info(request, f"This proforma was already converted to Sale #{proforma.converted_sale.id}.")
        return redirect("invoice", sale_id=proforma.converted_sale.id)

    with transaction.atomic():
        # Get or create customer record
        cust = proforma.customer
        if not cust and (proforma.buyer_company or proforma.buyer_name):
            cust = Customer.objects.create(
                name=proforma.buyer_name or proforma.buyer_company,
                company_name=proforma.buyer_company,
                tin_number=proforma.buyer_tin,
                vat_number=proforma.buyer_vat,
                phone=proforma.buyer_phone,
                address=proforma.buyer_address,
            )

        sale = Sale.objects.create(
            customer=cust,
            cashier=request.user,
            warehouse=proforma.warehouse,
            payment_method="CASH",
            total_amount=proforma.total_amount,
            subtotal_amount=proforma.subtotal_amount,
            tax_amount=proforma.tax_amount,
            status="APPROVED",
        )
        sale.fs_number = f"FS-{sale.id:06d}"
        sale.save()

        for item in proforma.items.all():
            prod = item.product
            cost_val = prod.cost_price if prod else 0.0
            
            # Deduct stock if linked to real product
            if prod:
                prod.quantity = max(prod.quantity - int(item.quantity), 0)
                prod.save()

            SaleItem.objects.create(
                sale=sale,
                product=prod,
                quantity=int(item.quantity),
                price=item.unit_price,
                cost_price=cost_val,
            )

        proforma.status = "CONVERTED"
        proforma.converted_sale = sale
        proforma.save()

    messages.success(request, f"Proforma {proforma.proforma_number} converted into official Sale #{sale.id}!")
    return redirect("invoice", sale_id=sale.id)
