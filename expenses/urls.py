from django.urls import path
from . import views

urlpatterns = [
    path("", views.ExpenseListView.as_view(), name="expense_list"),
    path("add/", views.ExpenseCreateView.as_view(), name="expense_add"),
    path("export/", views.export_expenses_csv, name="expense_export"),
    path("<int:pk>/edit/", views.ExpenseUpdateView.as_view(), name="expense_edit"),
    path("<int:pk>/delete/", views.ExpenseDeleteView.as_view(), name="expense_delete"),
]

