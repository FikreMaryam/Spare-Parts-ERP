from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from .views import CustomLoginView, home_view, dashboard_view, root_redirect, impersonate_auth, profile_view, backup_database_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("impersonate/auth/", impersonate_auth, name="impersonate_auth"),
    path("", root_redirect),
    path("home/", home_view, name="home"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile/", profile_view, name="user_profile"),
    path("backup/", backup_database_view, name="backup_database"),
    path("sales/", include("sales.urls")),
    path("inventory/", include("inventory.urls")),
    path("reports/", include("reports.urls")),
    path("hr/", include("hr.urls")),
    path("b2b/", include("b2b.urls")),
    path("store/", include("store.urls")),
    path("expenses/", include("expenses.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
