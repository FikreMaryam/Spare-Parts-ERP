from django.urls import path
from . import views, crud_views, views_proforma, views_payments, customer_io

urlpatterns = [
    path("pos/", views.pos_view, name="pos"),
    path("pos/<int:product_id>/", views.pos_single, name="pos_single"),
    path("scan-barcode/", views.scan_barcode_api, name="scan_barcode_api"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/", views.cart_view, name="cart"),
    path("invoice/<int:sale_id>/", views.invoice_view, name="invoice"),
    path("invoice/pdf/<int:sale_id>/", views.invoice_pdf, name="invoice_pdf"),
    path("report/", views.sales_report, name="sales_report"),
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/export/", customer_io.customer_export, name="customer_export"),
    path("customers/import/", customer_io.customer_import, name="customer_import"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/vehicles/add/", views.customer_add_vehicle, name="customer_add_vehicle"),
    path("customers/<int:pk>/vehicles/<int:vehicle_id>/delete/", views.customer_delete_vehicle, name="customer_delete_vehicle"),
    path("api/customers/<int:pk>/vehicles/", views.customer_vehicles_api, name="customer_vehicles_api"),
    path("pending-orders/", views.pending_orders, name="pending_orders"),

    # --- Mobile Banking & Automated Payment Reconciliation ---
    path("payments/", views_payments.payment_list, name="payment_list"),
    path("payments/record/", views_payments.payment_record, name="payment_record"),
    path("payments/<int:pk>/reconcile/", views_payments.payment_reconcile, name="payment_reconcile"),
    path("api/payments/verify/", views_payments.payment_verify_api, name="payment_verify_api"),

    # --- Proforma Invoices (የዋጋ ማቅረቢያ ፕሮፎርማ) ---
    path("proforma/", views_proforma.proforma_list, name="proforma_list"),
    path("proforma/create/", views_proforma.proforma_create, name="proforma_create"),
    path("proforma/<int:pk>/", views_proforma.proforma_detail, name="proforma_detail"),
    path("proforma/<int:pk>/pdf/", views_proforma.proforma_pdf, name="proforma_pdf"),
    path("proforma/<int:pk>/convert/", views_proforma.proforma_convert, name="proforma_convert"),

    # --- CRUD Views for Sales ---
    path("customers/add/", crud_views.CustomerCreateView.as_view(), name="customer_create"),
    path("customers/<int:pk>/edit/", crud_views.CustomerUpdateView.as_view(), name="customer_update"),
    path("customers/<int:pk>/delete/", crud_views.CustomerDeleteView.as_view(), name="customer_delete"),
]
