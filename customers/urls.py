from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('register/', views.register_tenant, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='customers/public_login.html'), name='public_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='public_logout'),
    path('saas/', views.saas_dashboard, name='saas_dashboard'),
    path('saas/impersonate/<int:tenant_id>/<int:user_id>/', views.impersonate_generate_token, name='impersonate_generate'),
]
