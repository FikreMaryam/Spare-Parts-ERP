from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth import login, get_user_model
from django.http import HttpResponseForbidden
from django.core import signing
from django.urls import reverse_lazy
from django.db.models import Sum

from inventory.models import Product
from sales.models import Sale
from expenses.models import Expense


def home_view(request):
    """Public home/landing page."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


class CustomLoginView(LoginView):
    """Login view that redirects to dashboard after login."""
    template_name = "registration/login.html"

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        if self.request.user.is_superuser:
            return reverse_lazy("admin:index")
        return reverse_lazy("dashboard")


@login_required
def dashboard_view(request):
    """Dashboard with stats and quick actions."""
    total_products = Product.objects.count()
    low_stock_count = sum(1 for p in Product.objects.all() if p.is_low_stock())
    total_sales = Sale.objects.count()
    total_revenue = Sale.objects.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
    recent_sales = Sale.objects.order_by("-date")[:10]

    return render(request, "dashboard.html", {
        "stats": {
            "total_products": total_products,
            "low_stock_count": low_stock_count,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
        },
        "recent_sales": recent_sales,
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
