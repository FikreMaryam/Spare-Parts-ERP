from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.partsouq_catalog, name='partsouq_catalog'),
    path('catalog/', views.partsouq_catalog, name='catalog'),
    path('products/', views.partsouq_catalog, name='product_list'),
    path('vin-lookup/', views.vin_lookup, name='vin_lookup'),

    path('vehicle/<int:model_id>/', views.vehicle_categories, name='vehicle_categories'),
    path('diagram/<int:pk>/', views.diagram_detail, name='diagram_detail'),
    path('oem-search/', views.oem_search, name='oem_search'),
    path('part/<int:pk>/', views.oem_part_detail, name='oem_part_detail'),
    path('product/<int:pk>/', views.oem_part_detail, name='product_detail'),
    path('add-to-cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),
    path('update-cart/<int:pk>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('about/', views.about_us, name='about_us'),
]