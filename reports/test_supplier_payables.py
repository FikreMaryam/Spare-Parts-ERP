from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from inventory.models import Purchase, Supplier
from .models import SupplierPayment


class SupplierPayablesTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="payables-user", password="test-pass")
        self.client.force_login(user)
        self.supplier = Supplier.objects.create(name="Parts Supplier")
        self.other_supplier = Supplier.objects.create(name="Other Supplier")

    def test_supplier_balances_are_not_double_counted_and_payments_are_recorded(self):
        Purchase.objects.create(supplier=self.supplier, total_amount=100)
        Purchase.objects.create(supplier=self.supplier, total_amount=50)
        SupplierPayment.objects.create(supplier=self.supplier, amount=20)
        SupplierPayment.objects.create(supplier=self.supplier, amount=10)

        response = self.client.get(reverse("supplier_payables"))

        self.assertEqual(response.status_code, 200)
        balance = next(
            row for row in response.context["supplier_balances"]
            if row["supplier"].pk == self.supplier.pk
        )
        self.assertEqual(balance["purchases"], Decimal("150.0"))
        self.assertEqual(balance["payments"], Decimal("30.00"))
        self.assertEqual(balance["balance"], Decimal("120.00"))

    def test_supplier_payment_can_be_recorded_for_matching_purchase(self):
        purchase = Purchase.objects.create(
            supplier=self.supplier,
            invoice_number="INV-100",
            total_amount=100,
        )

        response = self.client.post(
            reverse("supplier_payables"),
            {
                "supplier": self.supplier.pk,
                "purchase": purchase.pk,
                "amount": "25.50",
                "payment_date": "2026-03-26",
                "payment_method": "BANK_TRANSFER",
                "reference": "BANK-001",
                "notes": "Part payment",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        payment = SupplierPayment.objects.get()
        self.assertEqual(payment.amount, Decimal("25.50"))
        self.assertEqual(payment.purchase, purchase)
        self.assertEqual(payment.created_by.username, "payables-user")
        self.assertContains(response, "Supplier payment recorded.")

    def test_payment_rejects_a_purchase_from_another_supplier(self):
        purchase = Purchase.objects.create(supplier=self.other_supplier, total_amount=100)

        response = self.client.post(
            reverse("supplier_payables"),
            {
                "supplier": self.supplier.pk,
                "purchase": purchase.pk,
                "amount": "10",
                "payment_date": "2026-03-26",
                "payment_method": "CASH",
                "reference": "",
                "notes": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(SupplierPayment.objects.exists())
