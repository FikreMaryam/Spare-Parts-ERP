from django.urls import path
from .views import full_business_report
from .views import (
    pos_view,
    invoice_view,
    sales_report,
    invoice_pdf
)


urlpatterns = [
    path("pos/", pos_view, name="pos"),
    path("invoice/<int:sale_id>/", invoice_view, name="invoice"),
    path("invoice/pdf/<int:sale_id>/", invoice_pdf, name="invoice_pdf"),
    path("report/", sales_report, name="sales_report"),
    path("business-report/", full_business_report, name="business_report"),

    
]
