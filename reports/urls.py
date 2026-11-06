from django.urls import path
from . import views

urlpatterns = [
    # Dashboard & Executive Summary
    path("", views.reports_dashboard, name="reports_dashboard"),
    path("dashboard/", views.reports_dashboard, name="reports_dashboard_alias"),

    # Income Statement / Profit & Loss
    path("income-statement/", views.income_statement_view, name="income_statement"),
    path("income-statement/excel/", views.income_statement_excel, name="income_statement_excel"),
    path("income-statement/pdf/", views.income_statement_pdf, name="income_statement_pdf"),

    # Accounting Documents & Receipts
    path("vat-withholding-receipts/", views.vat_withholding_receipts_view, name="vat_withholding_receipts"),

    # Settings & Baselines
    path("settings/", views.business_profile_view, name="reports_settings"),
    path("opening-balance/", views.opening_balance_view, name="opening_balance"),
]
