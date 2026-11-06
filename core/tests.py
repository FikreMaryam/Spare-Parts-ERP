from datetime import date
import re

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from inventory.models import Product
from sales.models import Proforma


@override_settings(APP_NAME="Test Parts App")
class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="dashboard-user",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_dashboard_uses_database_inventory_aggregates(self):
        Product.objects.create(
            sku="LOW-STOCK",
            name="Low stock item",
            quantity=3,
            cost_price=10,
            selling_price=20,
        )
        Product.objects.create(
            sku="IN-STOCK",
            name="In stock item",
            quantity=8,
            cost_price=5,
            selling_price=10,
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["total_products"], 2)
        self.assertEqual(response.context["stats"]["low_stock_count"], 1)
        self.assertEqual(response.context["stats"]["total_inventory_value"], 70)
        self.assertContains(response, "Test Parts App")

        product_queries = [
            query["sql"].lower()
            for query in queries
            if 'from "inventory_product"' in query["sql"].lower()
        ]
        self.assertEqual(len(product_queries), 1)
        self.assertIn("sum(", product_queries[0])

    def test_language_switch_updates_dashboard_labels(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "am", "next": reverse("dashboard")},
        )

        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "ዳሽቦርድ")
        self.assertContains(response, "የዛሬ ሽያጭ")

    def test_proforma_pdf_renders_as_pdf(self):
        proforma = Proforma.objects.create(
            proforma_number="PRF-TEST-0001",
            valid_until=date(2027, 1, 1),
            buyer_name="Test Buyer",
            created_by=self.user,
        )

        response = self.client.get(reverse("proforma_pdf", args=[proforma.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertRegex(
            response.content,
            re.compile(rb"/MediaBox\s+\[\s+0\s+0\s+595\.2756\s+841\.8898\s+\]"),
        )
