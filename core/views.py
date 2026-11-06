import os
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, get_user_model
from django.http import HttpResponseForbidden
from django.core import signing
from django.urls import reverse_lazy
from django.db.models import Count, ExpressionWrapper, F, FloatField, Q, Sum
from django.conf import settings

from inventory.models import Product
from sales.models import Sale
from expenses.models import Expense
from reports.models import BusinessProfile


def home_view(request):
    """Public home/landing page."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


class CustomLoginView(LoginView):
    """Login view that redirects to dashboard after login."""
    template_name = "registration/login.html"

    def form_invalid(self, form):
        messages.error(self.request, "Incorrect username or password. Please try again.")
        return super().form_invalid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        if self.request.user.is_superuser:
            return reverse_lazy("admin:index")
        return reverse_lazy("dashboard")


@login_required
def dashboard_view(request):
    """Clean, high-performance dashboard with instant shop actions and core metrics."""
    import json
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    from sales.models import Sale, SaleItem, Proforma
    from inventory.models import Product, Warehouse

    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=6)

    # Core Store Metrics
    inventory_metrics = Product.objects.aggregate(
        total_products=Count("pk"),
        low_stock_count=Count(
            "pk",
            filter=Q(quantity__lte=Product.LOW_STOCK_THRESHOLD),
        ),
        total_inventory_value=Sum(
            ExpressionWrapper(
                F("quantity") * F("cost_price"),
                output_field=FloatField(),
            )
        ),
    )
    total_products = inventory_metrics["total_products"]
    low_stock_count = inventory_metrics["low_stock_count"]
    total_inventory_value = inventory_metrics["total_inventory_value"] or 0

    total_sales = Sale.objects.count()
    pending_orders_count = Sale.objects.filter(status='PENDING').count()
    total_revenue = Sale.objects.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

    # Today's Sales
    today_sales_qs = Sale.objects.filter(date__date=today, status__in=['APPROVED', 'SHIPPED'])
    today_sales_total = today_sales_qs.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    today_sales_count = today_sales_qs.count()

    # Multi-Shop & Proforma Counts
    warehouses_count = Warehouse.objects.filter(is_active=True).count()
    proformas_count = Proforma.objects.count()

    recent_sales = Sale.objects.select_related('customer', 'warehouse').order_by("-date")[:8]
    recent_proformas = Proforma.objects.select_related('customer').order_by("-date")[:5]

    # Last 7 days sales trend
    daily_sales = (
        Sale.objects.filter(date__date__gte=seven_days_ago)
        .annotate(sale_date=TruncDate('date'))
        .values('sale_date')
        .annotate(total=Sum('total_amount'))
        .order_by('sale_date')
    )
    
    sales_map = {item['sale_date'].strftime('%Y-%m-%d'): item['total'] for item in daily_sales if item['sale_date']}
    
    chart_sales_labels = []
    chart_sales_data = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        chart_sales_labels.append(day.strftime('%b %d'))
        chart_sales_data.append(sales_map.get(day_str, 0.0))
        
    # Top 5 Categories by sales volume
    top_categories = (
        SaleItem.objects.values('product__category__name')
        .annotate(total_qty=Sum('quantity'))
        .order_by('-total_qty')[:5]
    )
    
    chart_category_labels = []
    chart_category_data = []
    for cat in top_categories:
        name = cat['product__category__name'] or 'Uncategorized'
        chart_category_labels.append(name)
        chart_category_data.append(cat['total_qty'] or 0)

    return render(request, "dashboard.html", {
        "stats": {
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "total_inventory_value": total_inventory_value,
            "total_sales": total_sales,
            "today_sales_total": today_sales_total,
            "today_sales_count": today_sales_count,
            "pending_orders_count": pending_orders_count,
            "total_revenue": total_revenue,
            "warehouses_count": warehouses_count,
            "proformas_count": proformas_count,
        },
        "recent_sales": recent_sales,
        "recent_proformas": recent_proformas,
        "chart_sales_labels": json.dumps(chart_sales_labels),
        "chart_sales_data": json.dumps(chart_sales_data),
        "chart_category_labels": json.dumps(chart_category_labels),
        "chart_category_data": json.dumps(chart_category_data),
    })



@login_required
def root_redirect(request):
    """Root: redirect authenticated users to dashboard, others to home."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("home")


def impersonate_auth(request):
    """Verifies an impersonation token from the public schema and logs the user in."""
    token = request.GET.get("token")
    if not token:
        return HttpResponseForbidden("Missing token.")

    try:
        # Token is valid for 5 minutes
        data = signing.loads(token, salt="impersonate", max_age=300)
    except signing.BadSignature:
        return HttpResponseForbidden("Invalid or expired token.")

    user_id = data.get("user_id")
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        # Specify backend to avoid MultipleAuthBackends issues
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("dashboard")
    except User.DoesNotExist:
        return HttpResponseForbidden("User not found in tenant.")


from django import forms
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages

class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']


@login_required
def profile_view(request):
    """View and edit user profile plus core account settings."""
    user = request.user
    business_profile = BusinessProfile.get_profile()

    profile_form = ProfileForm(instance=user)
    password_form = PasswordChangeForm(user=user)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "update_profile":
            profile_form = ProfileForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been updated.")
                return redirect("user_profile")
        elif action == "change_password":
            password_form = PasswordChangeForm(user=user, data=request.POST)
            if password_form.is_valid():
                user_updated = password_form.save()
                update_session_auth_hash(request, user_updated)
                messages.success(request, "Your password has been changed.")
                return redirect("user_profile")
            else:
                messages.error(request, "Please correct the error below for your password change.")
        elif action == "update_account_settings":
            username = request.POST.get("username", "").strip()
            if username:
                if get_user_model().objects.filter(username__iexact=username).exclude(pk=user.pk).exists():
                    messages.error(request, "That username is already in use.")
                else:
                    user.username = username
                    user.save(update_fields=["username"])
                    messages.success(request, "Your account settings were updated.")
                    return redirect("user_profile")

    return render(request, "profile.html", {
        "profile_form": profile_form,
        "password_form": password_form,
        "business_profile": business_profile,
        "account_username": user.get_username(),
        "account_email": user.email,
        "account_full_name": user.get_full_name() or user.get_username(),
        "account_role": "Administrator" if user.is_superuser else "Staff User",
        "current_year": os.environ.get("CURRENT_YEAR", "2025"),
    })


@login_required
def backup_database_view(request):
    """1-Click Database Backup View supporting Excel (.xlsx), SQLite (.sqlite3), and JSON backups."""
    import os
    import time
    from io import BytesIO
    from django.http import HttpResponse
    from django.conf import settings
    from django.db import transaction
    from django.core import serializers

    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Only shop managers and admin accounts can download system backups.")
        return redirect("dashboard")

    backup_format = request.GET.get("format", "excel").lower()
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 1. EXCEL BACKUP (.xlsx) - Full Business Data Spreadsheet
    if backup_format == "excel":
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        wb = openpyxl.Workbook()

        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        cell_font = Font(name="Segoe UI", size=10)
        border_thin = Side(border_style="thin", color="CBD5E1")
        cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

        # Tab 1: Inventory Parts
        try:
            from inventory.models import Product
            ws1 = wb.active
            ws1.title = "Inventory Parts"
            ws1.append(["Part ID", "Name", "Category", "OEM / Part Number", "Cost Price ($)", "Selling Price ($)", "Quantity", "Min Reorder Qty", "Low Stock Alert"])
            for cell in ws1[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for p in Product.objects.select_related('category').all():
                cat_name = p.category.name if p.category else "Uncategorized"
                oem_val = getattr(p, 'oem_number', '') or getattr(p, 'part_number', '') or ''
                min_qty = getattr(p, 'min_quantity', 5)
                status = "LOW STOCK ALERT" if p.is_low_stock() else "OK"
                ws1.append([p.id, p.name, cat_name, oem_val, p.cost_price, p.price, p.quantity, min_qty, status])
        except Exception as e:
            pass

        # Tab 2: Sales History
        try:
            from sales.models import Sale
            ws2 = wb.create_sheet(title="Sales History")
            ws2.append(["Sale ID", "Customer Name", "Date & Time", "Payment Method", "Total Amount ($)", "Status"])
            for cell in ws2[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for s in Sale.objects.select_related('customer').order_by('-date'):
                cust_name = s.customer.name if s.customer else "Walk-in Customer"
                pay_method = s.get_payment_method_display() if hasattr(s, 'get_payment_method_display') else s.payment_method
                ws2.append([s.id, cust_name, s.date.strftime("%Y-%m-%d %H:%M"), pay_method, s.total_amount, s.status])
        except Exception as e:
            pass

        # Tab 3: Customers
        try:
            from sales.models import Customer
            ws3 = wb.create_sheet(title="Customers")
            ws3.append(["Customer ID", "Name", "Phone", "Email", "Credit Limit ($)", "Loyalty Points"])
            for cell in ws3[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for c in Customer.objects.all():
                ws3.append([c.id, c.name, c.phone, c.email, c.credit_limit, c.loyalty_points])
        except Exception as e:
            pass

        # Tab 4: Shop Expenses
        try:
            from expenses.models import Expense
            ws4 = wb.create_sheet(title="Shop Expenses")
            ws4.append(["Expense ID", "Description / Category", "Amount ($)", "Date"])
            for cell in ws4[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")

            for e in Expense.objects.all():
                desc = getattr(e, 'description', '') or getattr(e, 'title', '') or getattr(e, 'category', 'Expense')
                ws4.append([e.id, desc, e.amount, e.date.strftime("%Y-%m-%d")])
        except Exception as e:
            pass

        # Formatting column widths & styles
        for sheet in wb.worksheets:
            for col in sheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                try:
                    col_letter = get_column_letter(col[0].column)
                    sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
                except Exception:
                    pass
                for cell in col:
                    cell.font = cell_font
                    cell.border = cell_border

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="shop_erp_excel_backup_{timestamp}.xlsx"'
        return response

    # 2. DIRECT SQLITE FILE DOWNLOAD (If SQLite is active)
    db_engine = settings.DATABASES['default']['ENGINE']
    if backup_format == "sqlite" and 'sqlite3' in db_engine:
        db_path = settings.DATABASES['default']['NAME']
        if os.path.exists(db_path):
            with open(db_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/x-sqlite3')
                response['Content-Disposition'] = f'attachment; filename="shop_database_{timestamp}.sqlite3"'
                return response

    # 3. SAFE JSON SERIALIZATION (Works seamlessly on PostgreSQL & SQLite without cursor errors)
    from inventory.models import Product, Category, Supplier
    from sales.models import Sale, SaleItem, Customer
    from expenses.models import Expense
    from django.contrib.auth import get_user_model

    User = get_user_model()
    models_list = [Product, Category, Supplier, Sale, SaleItem, Customer, Expense, User]
    objects = []
    with transaction.atomic():
        for model in models_list:
            try:
                objects.extend(list(model.objects.all()))
            except Exception:
                pass

    json_data = serializers.serialize('json', objects, indent=2)
    response = HttpResponse(json_data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="shop_data_backup_{timestamp}.json"'
    return response


