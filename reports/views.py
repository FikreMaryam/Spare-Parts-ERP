from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import OuterRef, Subquery, Sum
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

from .models import BusinessProfile, OpeningBalance, CustomerPayment, SupplierPayment, StockCountAdjustment, VATWithholdingReceipt
from .services import get_date_range, get_financial_overview, get_income_statement_data
from .forms import SupplierPaymentForm
from inventory.models import Purchase, Supplier


@login_required
def reports_dashboard(request):
    """
    Executive Financial Dashboard:
    High-level business metrics, period comparisons, accounting health indicators,
    and direct navigation to all accounting sub-reports.
    """
    start_date, end_date, preset, prev_start, prev_end = get_date_range(request)
    
    current_metrics = get_financial_overview(start_date, end_date)
    prev_metrics = get_financial_overview(prev_start, prev_end)

    # Compute percentage growths
    def calc_growth(curr, prev):
        if prev and prev != 0:
            diff = curr - prev
            return round((diff / abs(prev)) * 100, 1)
        return None

    sales_growth = calc_growth(current_metrics["net_sales"], prev_metrics["net_sales"])
    profit_growth = calc_growth(current_metrics["net_profit"], prev_metrics["net_profit"])
    purchases_growth = calc_growth(current_metrics["total_purchases"], prev_metrics["total_purchases"])
    expenses_growth = calc_growth(current_metrics["total_expenses"], prev_metrics["total_expenses"])

    return render(request, "reports/dashboard.html", {
        "metrics": current_metrics,
        "prev_metrics": prev_metrics,
        "sales_growth": sales_growth,
        "profit_growth": profit_growth,
        "purchases_growth": purchases_growth,
        "expenses_growth": expenses_growth,
        "start_date": start_date,
        "end_date": end_date,
        "preset": preset,
        "prev_start": prev_start,
        "prev_end": prev_end,
    })


@login_required
def supplier_payables_view(request):
    if request.method == "POST":
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.save()
            messages.success(request, "Supplier payment recorded.")
            return redirect("supplier_payables")
    else:
        form = SupplierPaymentForm()

    purchase_totals = (
        Purchase.objects.filter(supplier_id=OuterRef("pk"))
        .order_by()
        .values("supplier_id")
        .annotate(total=Sum("total_amount"))
        .values("total")[:1]
    )
    payment_totals = (
        SupplierPayment.objects.filter(supplier_id=OuterRef("pk"))
        .order_by()
        .values("supplier_id")
        .annotate(total=Sum("amount"))
        .values("total")[:1]
    )
    suppliers = Supplier.objects.annotate(
        purchase_total=Subquery(purchase_totals),
        payment_total=Subquery(payment_totals),
    ).order_by("name")
    supplier_balances = []
    for supplier in suppliers:
        purchases = Decimal(str(supplier.purchase_total or 0))
        payments = Decimal(str(supplier.payment_total or 0))
        supplier_balances.append({
            "supplier": supplier,
            "purchases": purchases,
            "payments": payments,
            "balance": purchases - payments,
        })

    payments = SupplierPayment.objects.select_related(
        "supplier", "purchase", "created_by"
    ).order_by("-payment_date", "-id")[:100]
    return render(request, "reports/supplier_payables.html", {
        "form": form,
        "supplier_balances": supplier_balances,
        "payments": payments,
    })


@login_required
def income_statement_view(request):
    """
    Income Statement / Statement of Profit and Loss (P&L):
    Gross Sales, Sales Returns, Net Sales, COGS, Gross Profit, Operating Expenses, Net Profit.
    """
    start_date, end_date, preset, _, _ = get_date_range(request)
    data = get_income_statement_data(start_date, end_date)

    return render(request, "reports/income_statement.html", {
        "data": data,
        "start_date": start_date,
        "end_date": end_date,
        "preset": preset,
    })


@login_required
def income_statement_excel(request):
    """Export Income Statement to professional Excel workbook."""
    start_date, end_date, _, _, _ = get_date_range(request)
    data = get_income_statement_data(start_date, end_date)
    profile = data["profile"]

    wb = Workbook()
    ws = wb.active
    ws.title = "Income Statement"

    # Styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Arial", size=14, bold=True, color="FFFFFF")
    section_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    bold_font = Font(name="Arial", size=11, bold=True)
    regular_font = Font(name="Arial", size=10)
    title_font = Font(name="Arial", size=16, bold=True)
    muted_font = Font(name="Arial", size=9, color="64748B")

    # Business Header
    ws.cell(row=1, column=1, value=profile.name).font = title_font
    ws.cell(row=2, column=1, value="STATEMENT OF PROFIT AND LOSS (INCOME STATEMENT)").font = bold_font
    ws.cell(row=3, column=1, value=f"Period: {start_date} to {end_date} | Currency: {profile.currency_code}").font = muted_font
    if profile.tin_number:
        ws.cell(row=4, column=1, value=f"TIN: {profile.tin_number} | VAT Reg: {'Yes (15%)' if profile.vat_registered else 'No'}").font = muted_font

    start_row = 6
    ws.cell(row=start_row, column=1, value="Account / Line Item").font = bold_font
    ws.cell(row=start_row, column=2, value=f"Amount ({profile.currency_code})").font = bold_font
    ws.cell(row=start_row, column=1).fill = section_fill
    ws.cell(row=start_row, column=2).fill = section_fill

    rows = [
        ("REVENUE / SALES", ""),
        ("  Gross Sales", data["gross_sales"]),
        ("  Less: Sales Returns / Cancellations", -data["sales_returns"]),
        ("Net Sales Revenue", data["net_sales"]),
    ]

    if profile.vat_registered:
        rows.extend([
            ("  Less: VAT Collected (15% applicable)", -data["vat_collected"]),
            ("Net Sales Revenue (Excl. VAT)", data["net_sales_ex_vat"]),
        ])

    rows.extend([
        ("", ""),
        ("COST OF GOODS SOLD (COGS)", ""),
        ("  Opening Inventory Value", data["opening_inventory_value"]),
        ("  Add: Net Purchases (Direct Inventory)", data["total_purchases"]),
        ("  Goods Available for Sale", data["goods_available_for_sale"]),
        ("  Less: Closing Inventory Value", -data["closing_inventory_value"]),
        ("Cost of Goods Sold (COGS)", data["cogs"]),
        ("", ""),
        ("GROSS PROFIT", data["gross_profit"]),
        ("", ""),
        ("OPERATING EXPENSES", ""),
    ])

    for exp in data["expense_categories"]:
        rows.append((f"  {exp['label']}", exp["amount"]))

    rows.extend([
        ("Total Operating Expenses", data["total_expenses"]),
        ("", ""),
        ("NET OPERATING PROFIT / (LOSS)", data["net_profit"]),
    ])

    curr_row = start_row + 1
    for label, val in rows:
        c1 = ws.cell(row=curr_row, column=1, value=label)
        c2 = ws.cell(row=curr_row, column=2)

        if isinstance(val, (int, float)):
            c2.value = round(val, 2)
            c2.number_format = "#,##0.00"

        if label in ["REVENUE / SALES", "COST OF GOODS SOLD (COGS)", "OPERATING EXPENSES"]:
            c1.font = bold_font
            c1.fill = section_fill
            c2.fill = section_fill
        elif label in ["Net Sales Revenue", "Net Sales Revenue (Excl. VAT)", "Cost of Goods Sold (COGS)", "Total Operating Expenses"]:
            c1.font = bold_font
            c2.font = bold_font
        elif label in ["GROSS PROFIT", "NET OPERATING PROFIT / (LOSS)"]:
            c1.font = bold_font
            c2.font = bold_font
            c1.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
            c2.fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")

        curr_row += 1

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 22

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="income_statement_{start_date}_{end_date}.xlsx"'
    wb.save(response)
    return response


@login_required
def income_statement_pdf(request):
    """Export Income Statement to print-ready PDF document."""
    start_date, end_date, _, _, _ = get_date_range(request)
    data = get_income_statement_data(start_date, end_date)
    profile = data["profile"]

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin

    # Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(margin, y, profile.name)
    y -= 18

    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin, y, "STATEMENT OF PROFIT AND LOSS (INCOME STATEMENT)")
    y -= 14

    p.setFont("Helvetica", 9)
    p.setFillColorRGB(0.3, 0.3, 0.35)
    p.drawString(margin, y, f"Period: {start_date} to {end_date} | Currency: {profile.currency_code} | Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
    if profile.tin_number:
        y -= 12
        p.drawString(margin, y, f"TIN: {profile.tin_number} | Address: {profile.address}")
    p.setFillColorRGB(0, 0, 0)
    y -= 25

    # Draw separator line
    p.setLineWidth(1)
    p.line(margin, y, width - margin, y)
    y -= 20

    def draw_row(label, val, is_header=False, is_total=False, is_grand_total=False):
        nonlocal y
        if is_header:
            p.setFont("Helvetica-Bold", 10)
            p.setFillColorRGB(0.1, 0.2, 0.4)
            p.drawString(margin, y, label)
            p.setFillColorRGB(0, 0, 0)
        elif is_grand_total:
            p.setFont("Helvetica-Bold", 11)
            p.drawString(margin, y, label)
            if val is not None:
                p.drawRightString(width - margin, y, f"{val:,.2f} {profile.currency_code}")
            y -= 4
            p.setLineWidth(1.5)
            p.line(margin, y, width - margin, y)
        elif is_total:
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margin + 10, y, label)
            if val is not None:
                p.drawRightString(width - margin, y, f"{val:,.2f}")
            y -= 2
            p.setLineWidth(0.5)
            p.line(margin + 10, y, width - margin, y)
        else:
            p.setFont("Helvetica", 9)
            p.drawString(margin + 20, y, label)
            if val is not None:
                p.drawRightString(width - margin, y, f"{val:,.2f}")
        y -= 16

    draw_row("1. REVENUE", None, is_header=True)
    draw_row("Gross Sales", data["gross_sales"])
    if data["sales_returns"] > 0:
        draw_row("Less: Sales Returns & Cancellations", -data["sales_returns"])
    draw_row("Net Sales Revenue", data["net_sales"], is_total=True)
    if profile.vat_registered:
        draw_row("Less: VAT Collected (15%)", -data["vat_collected"])
        draw_row("Net Sales (Excluding VAT)", data["net_sales_ex_vat"], is_total=True)
    y -= 8

    draw_row("2. COST OF GOODS SOLD (COGS)", None, is_header=True)
    if data["has_opening_inventory"]:
        draw_row("Opening Inventory Valuation", data["opening_inventory_value"])
        draw_row("Add: Net Purchases", data["total_purchases"])
        draw_row("Goods Available for Sale", data["goods_available_for_sale"])
        draw_row("Less: Closing Inventory Valuation", -data["closing_inventory_value"])
    draw_row("Cost of Goods Sold (COGS)", data["cogs"], is_total=True)
    y -= 8

    draw_row("GROSS PROFIT", data["gross_profit"], is_grand_total=True)
    y -= 10

    draw_row("3. OPERATING EXPENSES", None, is_header=True)
    for exp in data["expense_categories"]:
        draw_row(f"{exp['label']}", exp["amount"])
    draw_row("Total Operating Expenses", data["total_expenses"], is_total=True)
    y -= 10

    draw_row("NET PROFIT / (LOSS)", data["net_profit"], is_grand_total=True)

    y -= 25
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.4, 0.4, 0.45)
    p.drawString(margin, y, "Draft Management Financial Statement. For internal use and Ethiopian tax filing preparation.")

    p.showPage()
    p.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="income_statement_{start_date}_{end_date}.pdf"'
    return response


@login_required
def vat_withholding_receipts_view(request):
    """Upload and review VAT withholding receipts issued by companies or suppliers."""
    receipts = VATWithholdingReceipt.objects.all().order_by("-created_at")

    if request.method == "POST":
        company_name = request.POST.get("company_name", "").strip()
        tin_number = request.POST.get("tin_number", "").strip()
        withholding_period = request.POST.get("withholding_period", "").strip()
        amount_value = request.POST.get("amount", "0").strip()
        notes = request.POST.get("notes", "").strip()
        receipt_file = request.FILES.get("receipt_file")

        if not company_name:
            messages.error(request, "Company name is required for the withholding receipt.")
        else:
            try:
                amount = Decimal(amount_value or 0)
            except InvalidOperation:
                messages.error(request, "Please enter a valid withholding amount.")
                amount = Decimal("0")

            if amount < 0:
                messages.error(request, "Withholding amount cannot be negative.")
            else:
                VATWithholdingReceipt.objects.create(
                    company_name=company_name,
                    tin_number=tin_number,
                    withholding_period=withholding_period,
                    amount=amount,
                    notes=notes,
                    receipt_file=receipt_file,
                )
                messages.success(request, "VAT withholding receipt saved successfully.")
                return redirect("vat_withholding_receipts")

    return render(request, "reports/vat_withholding_receipts.html", {"receipts": receipts})


@login_required
def business_profile_view(request):
    """Settings page to configure shop details, TIN, VAT, and currency."""
    profile = BusinessProfile.get_profile()

    if request.method == "POST":
        profile.name = request.POST.get("name", "").strip() or profile.name
        profile.trade_name = request.POST.get("trade_name", "").strip()
        profile.tin_number = request.POST.get("tin_number", "").strip()
        profile.vat_registered = "vat_registered" in request.POST
        try:
            profile.vat_rate_percent = float(request.POST.get("vat_rate_percent", 15.0))
        except ValueError:
            pass
        profile.phone = request.POST.get("phone", "").strip()
        profile.email = request.POST.get("email", "").strip()
        profile.address = request.POST.get("address", "").strip()
        profile.currency_code = request.POST.get("currency_code", "ETB").strip() or "ETB"
        profile.save()
        messages.success(request, "Business profile & accounting settings updated successfully.")
        return redirect("reports_settings")

    return render(request, "reports/settings.html", {"profile": profile})


@login_required
def opening_balance_view(request):
    """View and record financial baseline opening balances."""
    baselines = OpeningBalance.objects.all().order_by("-effective_date")
    current_baseline = baselines.first()

    if request.method == "POST":
        effective_date = request.POST.get("effective_date")
        cash = request.POST.get("opening_cash", "0") or "0"
        bank = request.POST.get("opening_bank", "0") or "0"
        mobile = request.POST.get("opening_mobile_money", "0") or "0"
        inventory = request.POST.get("opening_inventory_value", "0") or "0"
        receivables = request.POST.get("opening_receivables", "0") or "0"
        payables = request.POST.get("opening_payables", "0") or "0"
        equipment = request.POST.get("opening_equipment_assets", "0") or "0"
        capital = request.POST.get("owner_capital", "0") or "0"
        notes = request.POST.get("notes", "").strip()

        try:
            OpeningBalance.objects.create(
                effective_date=effective_date,
                opening_cash=float(cash),
                opening_bank=float(bank),
                opening_mobile_money=float(mobile),
                opening_inventory_value=float(inventory),
                opening_receivables=float(receivables),
                opening_payables=float(payables),
                opening_equipment_assets=float(equipment),
                owner_capital=float(capital),
                notes=notes,
            )
            messages.success(request, f"Opening balance baseline for {effective_date} recorded successfully.")
            return redirect("opening_balance")
        except Exception as e:
            messages.error(request, f"Error saving opening balance: {e}")

    return render(request, "reports/opening_balance.html", {
        "baselines": baselines,
        "current_baseline": current_baseline,
    })
