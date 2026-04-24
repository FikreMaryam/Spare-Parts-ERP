from django.urls import path
from . import views, crud_views

urlpatterns = [
    path("pos/", views.pos_view, name="pos"),
    path("pos/<int:product_id>/", views.pos_single, name="pos_single"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/", views.cart_view, name="cart"),
    path("invoice/<int:sale_id>/", views.invoice_view, name="invoice"),
    path("invoice/pdf/<int:sale_id>/", views.invoice_pdf, name="invoice_pdf"),
    path("report/", views.sales_report, name="sales_report"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("pending-orders/", views.pending_orders, name="pending_orders"),

    # --- CRUD Views for Sales ---
    path("customers/add/", crud_views.CustomerCreateView.as_view(), name="customer_create"),
    path("customers/<int:pk>/edit/", crud_views.CustomerUpdateView.as_view(), name="customer_update"),
    path("customers/<int:pk>/delete/", crud_views.CustomerDeleteView.as_view(), name="customer_delete"),
]
