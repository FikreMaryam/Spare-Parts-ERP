from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Expense

User = get_user_model()


class ExpenseViewTests(TestCase):
    def setUp(self):
        # Create normal staff user (not superuser)
        self.staff_user = User.objects.create_user(username="staff", password="pass", is_active=True)
        self.client.force_login(self.staff_user)

    def test_expense_list_accessible(self):
        url = reverse("expense_list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_create_and_edit_expense(self):
        add_url = reverse("expense_add")
        data = {
            "title": "Shop Electricity Bill",
            "category": "UTILITY",
            "amount": "150.50",
            "date": "2026-08-15",
        }
        resp = self.client.post(add_url, data)
        self.assertEqual(resp.status_code, 302)

        expense = Expense.objects.get(title="Shop Electricity Bill")
        self.assertEqual(expense.amount, 150.50)
        self.assertEqual(str(expense.date), "2026-08-15")

        edit_url = reverse("expense_edit", args=[expense.pk])
        resp = self.client.post(edit_url, {
            "title": "Shop Electricity Bill - Updated",
            "category": "UTILITY",
            "amount": "175.00",
            "date": "2026-08-15",
        })
        self.assertEqual(resp.status_code, 302)

        expense.refresh_from_db()
        self.assertEqual(expense.title, "Shop Electricity Bill - Updated")
        self.assertEqual(expense.amount, 175.00)

