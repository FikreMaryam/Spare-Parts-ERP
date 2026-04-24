from django.urls import path
from . import views, crud_views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("export/", views.export_inventory, name="export_inventory"),
    path("import/", views.import_inventory, name="import_inventory"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("stock/", views.stockmovement_list, name="stockmovement_list"),
    path("attributes/", views.attributes_dashboard, name="inventory_attributes"),
    path("purchases/", views.purchase_list, name="purchase_list"),
    path("purchases/add/", views.purchase_add, name="purchase_add"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),

    # --- CRUD Views for Inventory ---
    # Products
    path("product/add/", crud_views.ProductCreateView.as_view(), name="product_create"),
    path("product/<int:pk>/edit/", crud_views.ProductUpdateView.as_view(), name="product_update"),
    path("product/<int:pk>/delete/", crud_views.ProductDeleteView.as_view(), name="product_delete"),
    
    # Warehouses (add/edit/delete; list is in views)
    path("warehouses/add/", crud_views.WarehouseCreateView.as_view(), name="warehouse_create"),
    path("warehouses/<int:pk>/edit/", crud_views.WarehouseUpdateView.as_view(), name="warehouse_update"),
    path("warehouses/<int:pk>/delete/", crud_views.WarehouseDeleteView.as_view(), name="warehouse_delete"),
    
    # Categories
    path("categories/", crud_views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", crud_views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", crud_views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", crud_views.CategoryDeleteView.as_view(), name="category_delete"),
    
    # Car Makes
    path("carmakes/", crud_views.CarMakeListView.as_view(), name="carmake_list"),
    path("carmakes/add/", crud_views.CarMakeCreateView.as_view(), name="carmake_create"),
    path("carmakes/<int:pk>/edit/", crud_views.CarMakeUpdateView.as_view(), name="carmake_update"),
    path("carmakes/<int:pk>/delete/", crud_views.CarMakeDeleteView.as_view(), name="carmake_delete"),

    # Car Models
    path("carmodels/", crud_views.CarModelListView.as_view(), name="carmodel_list"),
    path("carmodels/add/", crud_views.CarModelCreateView.as_view(), name="carmodel_create"),
    path("carmodels/<int:pk>/edit/", crud_views.CarModelUpdateView.as_view(), name="carmodel_update"),
    path("carmodels/<int:pk>/delete/", crud_views.CarModelDeleteView.as_view(), name="carmodel_delete"),

    # Suppliers
    path("suppliers/", crud_views.SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/add/", crud_views.SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", crud_views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("suppliers/<int:pk>/delete/", crud_views.SupplierDeleteView.as_view(), name="supplier_delete"),
]
