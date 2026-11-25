from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Customer


class CustomerCsvTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="customer-csv-user", password="test-pass")
        self.client.force_login(user)

    def test_import_adds_valid_rows_and_skips_duplicate_customers(self):
        Customer.objects.create(name="Existing Customer", email="existing@example.com")
        upload = SimpleUploadedFile(
            "customers.csv",
            (
                "name,company_name,tin_number,vat_number,phone,email,address,credit_limit\n"
                "New Contact,New Company,123,456,0911000000,new@example.com,Addis,2500\n"
                "Another Contact,,,,,existing@example.com,,0\n"
            ).encode(),
            content_type="text/csv",
        )

        response = self.client.post(reverse("customer_import"), {"file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Customer.objects.count(), 2)
        customer = Customer.objects.get(email="new@example.com")
        self.assertEqual(customer.company_name, "New Company")
        self.assertEqual(str(customer.credit_limit), "2500.00")
        self.assertContains(response, "Imported 1 customer(s); skipped 1 duplicate(s).")

    def test_import_rejects_csv_without_a_name_column(self):
        upload = SimpleUploadedFile("bad.csv", b"email,phone\nx@example.com,123\n")

        response = self.client.post(reverse("customer_import"), {"file": upload}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertIn(
            "The CSV must include a 'name' column.",
            str(list(response.context["messages"])[0]),
        )

    def test_export_escapes_spreadsheet_formulas(self):
        Customer.objects.create(name="=HYPERLINK(\"bad\")", email="customer@example.com")

        response = self.client.get(reverse("customer_export"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("'=HYPERLINK", response.content.decode("utf-8-sig"))
