from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('add/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
]