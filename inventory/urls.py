from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("export/", views.export_inventory, name="export_inventory"),
    path("import/", views.import_inventory, name="import_inventory"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_add, name="purchase_add"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
]
