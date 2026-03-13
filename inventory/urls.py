from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("export/", views.export_inventory, name="export_inventory"),
    path("import/", views.import_inventory, name="import_inventory"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("stock/", views.stockmovement_list, name="stockmovement_list"),
    path("accounts/", views.account_list, name="account_list"),
    path("journal/", views.journalentry_list, name="journalentry_list"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_add, name="purchase_add"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
]
