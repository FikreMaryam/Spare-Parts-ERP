from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='store_home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
]