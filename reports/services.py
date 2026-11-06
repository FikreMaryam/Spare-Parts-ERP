from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q, Count, F

from inventory.models import Product, Purchase, PurchaseItem, StockMovement, Category, Supplier
from sales.models import Sale, SaleItem, Customer
from expenses.models import Expense
from .models import BusinessProfile, OpeningBalance, CustomerPayment, SupplierPayment, StockCountAdjustment


def get_date_range(request):
    """
    Parses request GET parameters for date presets or custom start/end dates.
    Returns: (start_date, end_date, preset_name, prev_start_date, prev_end_date)
    """
    today = timezone.now().date()
    preset = request.GET.get("period", "this_month").strip()
    date_from_str = request.GET.get("date_from", "").strip()
    date_to_str = request.GET.get("date_to", "").strip()

    if date_from_str and date_to_str:
        try:
            start_date = datetime.strptime(date_from_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(date_to_str, "%Y-%m-%d").date()
            preset = "custom"
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
            preset = "this_month"
    elif preset == "today":
        start_date = today
        end_date = today
    elif preset == "this_week":
        # Monday to Sunday of current week
        start_date = today - timedelta(days=today.weekday())
        end_date = today
    elif preset == "this_month":
        start_date = today.replace(day=1)
        end_date = today
    elif preset == "this_quarter":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_month, day=1)
        end_date = today
    elif preset == "this_year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif preset == "last_month":
        first_of_this_month = today.replace(day=1)
        end_date = first_of_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    elif preset == "last_year":
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year - 1, 12, 31)
    elif preset == "all_time":
        first_sale = Sale.objects.order_by("date").first()
        start_date = first_sale.date.date() if first_sale else today - timedelta(days=365)
        end_date = today
    else:
        # Default: current month
        start_date = today.replace(day=1)
        end_date = today
        preset = "this_month"

    # Compute equivalent previous period for comparison
    period_days = (end_date - start_date).days + 1
    prev_end_date = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=period_days - 1)

    return start_date, end_date, preset, prev_start_date, prev_end_date


def get_financial_overview(start_date, end_date):
    """
    Computes executive metrics for the given period.
    """
    profile = BusinessProfile.get_profile()

    # Sales
    approved_sales = Sale.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        status__in=["APPROVED", "SHIPPED"]
    )
    gross_sales = float(approved_sales.aggregate(total=Sum("total_amount"))["total"] or 0.0)
    sales_count = approved_sales.count()

    cancelled_sales = Sale.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date,
        status="CANCELLED"
    )
    sales_returns = float(cancelled_sales.aggregate(total=Sum("total_amount"))["total"] or 0.0)
    net_sales = max(gross_sales - sales_returns, 0.0)

    # VAT Separation
    vat_rate = float(profile.vat_rate_percent) / 100.0 if profile.vat_registered else 0.0
    if profile.vat_registered and vat_rate > 0:
        net_sales_ex_vat = net_sales / (1.0 + vat_rate)
        vat_collected = net_sales - net_sales_ex_vat
    else:
        net_sales_ex_vat = net_sales
        vat_collected = 0.0

    # Purchases
    purchases_qs = Purchase.objects.filter(date__date__gte=start_date, date__date__lte=end_date)
    total_purchases = float(purchases_qs.aggregate(total=Sum("total_amount"))["total"] or 0.0)
    purchases_count = purchases_qs.count()

    # Expenses
    expenses_qs = Expense.objects.filter(date__gte=start_date, date__lte=end_date)
    total_expenses = float(expenses_qs.aggregate(total=Sum("amount"))["total"] or 0.0)

    # Inventory Valuation (Current Snapshot)
    all_products = Product.objects.all()
    total_products = all_products.count()
    low_stock_count = sum(1 for p in all_products if p.is_low_stock())
    out_of_stock_count = all_products.filter(quantity=0).count()
    closing_inventory_value = sum(float(p.quantity * p.cost_price) for p in all_products)
    closing_inventory_retail = sum(float(p.quantity * p.selling_price) for p in all_products)
    potential_inventory_margin = closing_inventory_retail - closing_inventory_value

    # Cost of Goods Sold (Direct transactional COGS based on SaleItems during period)
    sale_items = SaleItem.objects.filter(
        sale__date__date__gte=start_date,
        sale__date__date__lte=end_date,
        sale__status__in=["APPROVED", "SHIPPED"]
    )
    cogs_transactional = sum(float(item.quantity * item.cost_price) for item in sale_items)

    # Opening Inventory baseline
    opening_rec = OpeningBalance.objects.filter(effective_date__lte=start_date).order_by("-effective_date").first()
    has_opening_inventory = opening_rec is not None and opening_rec.opening_inventory_value > 0
    opening_inventory_value = float(opening_rec.opening_inventory_value) if has_opening_inventory else 0.0

    # Accounting formula COGS = Opening + Purchases - Closing
    if has_opening_inventory:
        cogs_periodic = max(opening_inventory_value + total_purchases - closing_inventory_value, 0.0)
        cogs_final = cogs_periodic
        cogs_method = "Periodic (Opening + Purchases − Closing)"
    else:
        cogs_final = cogs_transactional
        cogs_method = "Perpetual / Transactional (Sum of unit costs at sale)"

    gross_profit = net_sales_ex_vat - cogs_final
    net_profit = gross_profit - total_expenses
    gross_margin_percent = (gross_profit / net_sales_ex_vat * 100) if net_sales_ex_vat > 0 else 0.0
    net_margin_percent = (net_profit / net_sales_ex_vat * 100) if net_sales_ex_vat > 0 else 0.0

    # Receivables (Credit Sales minus Customer Payments)
    credit_sales_total = float(Sale.objects.filter(payment_method="CREDIT", status__in=["APPROVED", "SHIPPED"]).aggregate(total=Sum("total_amount"))["total"] or 0.0)
    customer_payments_total = float(CustomerPayment.objects.aggregate(total=Sum("amount"))["total"] or 0.0)
    opening_receivables = float(opening_rec.opening_receivables) if opening_rec else 0.0
    total_receivables = max(opening_receivables + credit_sales_total - customer_payments_total, 0.0)

    # Payables (Purchases minus Supplier Payments)
    all_purchases_total = float(Purchase.objects.aggregate(total=Sum("total_amount"))["total"] or 0.0)
    supplier_payments_total = float(SupplierPayment.objects.aggregate(total=Sum("amount"))["total"] or 0.0)
    opening_payables = float(opening_rec.opening_payables) if opening_rec else 0.0
    total_payables = max(opening_payables + all_purchases_total - supplier_payments_total, 0.0)

    # Cash & Liquid Balances
    cash_sales = float(Sale.objects.filter(payment_method="CASH", status__in=["APPROVED", "SHIPPED"]).aggregate(total=Sum("total_amount"))["total"] or 0.0)
    bank_sales = float(Sale.objects.filter(payment_method__in=["TRANSFER", "ATM"], status__in=["APPROVED", "SHIPPED"]).aggregate(total=Sum("total_amount"))["total"] or 0.0)
    mobile_sales = float(Sale.objects.filter(payment_method="MOBILE", status__in=["APPROVED", "SHIPPED"]).aggregate(total=Sum("total_amount"))["total"] or 0.0)

    opening_cash = float(opening_rec.opening_cash) if opening_rec else 0.0
    opening_bank = float(opening_rec.opening_bank) if opening_rec else 0.0
    opening_mobile = float(opening_rec.opening_mobile_money) if opening_rec else 0.0

    return {
        "profile": profile,
        "start_date": start_date,
        "end_date": end_date,
        "gross_sales": gross_sales,
        "sales_returns": sales_returns,
        "net_sales": net_sales,
        "net_sales_ex_vat": net_sales_ex_vat,
        "vat_collected": vat_collected,
        "sales_count": sales_count,
        "total_purchases": total_purchases,
        "purchases_count": purchases_count,
        "total_expenses": total_expenses,
        "cogs": cogs_final,
        "cogs_method": cogs_method,
        "has_opening_inventory": has_opening_inventory,
        "opening_inventory_value": opening_inventory_value,
        "closing_inventory_value": closing_inventory_value,
        "closing_inventory_retail": closing_inventory_retail,
        "potential_inventory_margin": potential_inventory_margin,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "gross_margin_percent": gross_margin_percent,
        "net_margin_percent": net_margin_percent,
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_receivables": total_receivables,
        "total_payables": total_payables,
        "cash_sales": cash_sales,
        "bank_sales": bank_sales,
        "mobile_sales": mobile_sales,
        "opening_cash": opening_cash,
        "opening_bank": opening_bank,
        "opening_mobile": opening_mobile,
    }


def get_income_statement_data(start_date, end_date):
    """
    Detailed Income Statement (Profit & Loss) calculation matching strict accounting standards.
    Formula:
      Net Sales = Gross Sales - Sales Returns/Discounts
      COGS = Opening Inventory + Net Purchases + Direct Costs - Closing Inventory
      Gross Profit = Net Sales - COGS
      Operating Expenses = Sum of categorical business expenses
      Net Operating Profit = Gross Profit - Operating Expenses
    """
    profile = BusinessProfile.get_profile()
    overview = get_financial_overview(start_date, end_date)

    # Detailed Expense Breakdown by Category
    expenses_qs = Expense.objects.filter(date__gte=start_date, date__lte=end_date)
    expense_categories = []
    category_map = dict(Expense.CATEGORY_CHOICES)
    
    for code, label in Expense.CATEGORY_CHOICES:
        cat_amount = float(expenses_qs.filter(category=code).aggregate(total=Sum("amount"))["total"] or 0.0)
        if cat_amount > 0:
            expense_categories.append({
                "code": code,
                "label": label,
                "amount": cat_amount,
                "percentage": (cat_amount / overview["total_expenses"] * 100) if overview["total_expenses"] > 0 else 0.0
            })

    # Add any other expense categories present in records
    other_cats = expenses_qs.exclude(category__in=category_map.keys()).values("category").annotate(total=Sum("amount"))
    for item in other_cats:
        cat_amount = float(item["total"] or 0.0)
        if cat_amount > 0:
            expense_categories.append({
                "code": item["category"],
                "label": item["category"].capitalize(),
                "amount": cat_amount,
                "percentage": (cat_amount / overview["total_expenses"] * 100) if overview["total_expenses"] > 0 else 0.0
            })

    # Missing Data Warnings
    warnings = []
    if not overview["has_opening_inventory"]:
        warnings.append({
            "type": "warning",
            "title": "Missing Formal Opening Inventory",
            "message": "No Opening Balance record was found on or before this period. COGS is calculated directly from line-item unit costs (perpetual costing). To use periodic costing, record an Opening Balance."
        })
    if overview["purchases_count"] == 0 and overview["sales_count"] > 0:
        warnings.append({
            "type": "info",
            "title": "Zero Purchases Recorded in Period",
            "message": "No purchase orders were logged between these dates. Existing warehouse stock was used to fulfill customer sales."
        })

    return {
        **overview,
        "expense_categories": expense_categories,
        "warnings": warnings,
        "goods_available_for_sale": overview["opening_inventory_value"] + overview["total_purchases"],
    }
