from django.urls import path
from .views import full_business_report
from .views import (
    pos_view,
    pos_single,
    add_to_cart,
    remove_from_cart,
    cart_view,
    invoice_view,
    sales_report,
    invoice_pdf,
    customer_list,
    customer_detail,
)


urlpatterns = [
    path("pos/", pos_view, name="pos"),
    path("pos/<int:product_id>/", pos_single, name="pos_single"),
    path("cart/add/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", remove_from_cart, name="remove_from_cart"),
    path("cart/", cart_view, name="cart"),
    path("invoice/<int:sale_id>/", invoice_view, name="invoice"),
    path("invoice/pdf/<int:sale_id>/", invoice_pdf, name="invoice_pdf"),
    path("report/", sales_report, name="sales_report"),
    path("business-report/", full_business_report, name="business_report"),
    path("customers/", customer_list, name="customer_list"),
    path("customers/<int:pk>/", customer_detail, name="customer_detail"),
]
