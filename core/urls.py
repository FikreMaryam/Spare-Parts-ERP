from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from .views import CustomLoginView, home_view, dashboard_view, root_redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", root_redirect),
    path("home/", home_view, name="home"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("sales/", include("sales.urls")),
    path("inventory/", include("inventory.urls")),
    path("hr/", include("hr.urls")),
    path("store/", include("store.urls")),
]


