from django.test import TestCase
from django.urls import reverse
from decimal import Decimal
from django.contrib.auth import get_user_model

from inventory.models import CarMake, CarModel, Product
from reports.models import BusinessProfile
from .models import Customer, Proforma, Sale, SaleItem


class CustomerManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="customer-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_customer_form_includes_company_and_tax_details(self):
        response = self.client.get(reverse("customer_create"))

        self.assertEqual(response.status_code, 200)
        for field in (
            "company_name",
            "tin_number",
            "vat_number",
            "phone",
            "email",
            "address",
            "credit_limit",
        ):
            self.assertContains(response, f'name="{field}"')

    def test_create_and_update_customer_company_details(self):
        response = self.client.post(
            reverse("customer_create"),
            {
                "name": "Alemu Bekele",
                "company_name": "Alemu Auto Garage",
                "tin_number": "0012345678",
                "vat_number": "VAT-12345",
                "phone": "+251911000000",
                "email": "garage@example.com",
                "address": "Addis Ababa",
                "credit_limit": "25000.00",
            },
        )

        self.assertRedirects(response, reverse("customer_list"))
        customer = Customer.objects.get(tin_number="0012345678")
        self.assertEqual(customer.company_name, "Alemu Auto Garage")
        self.assertEqual(customer.vat_number, "VAT-12345")
        self.assertEqual(customer.credit_limit, Decimal("25000.00"))

        response = self.client.post(
            reverse("customer_update", args=[customer.pk]),
            {
                "name": "Alemu Bekele",
                "company_name": "Alemu Auto Parts",
                "tin_number": "0098765432",
                "vat_number": "",
                "phone": "+251911000000",
                "email": "garage@example.com",
                "address": "Addis Ababa",
                "credit_limit": "30000.00",
            },
        )

        self.assertRedirects(response, reverse("customer_list"))
        customer.refresh_from_db()
        self.assertEqual(customer.company_name, "Alemu Auto Parts")
        self.assertEqual(customer.tin_number, "0098765432")
        self.assertEqual(customer.credit_limit, Decimal("30000.00"))

    def test_customer_credit_limit_cannot_be_negative(self):
        response = self.client.post(
            reverse("customer_create"),
            {
                "name": "Test Customer",
                "credit_limit": "-1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Customer.objects.exists())
        self.assertContains(response, "Credit limit cannot be negative.")

    def test_customer_list_searches_business_fields(self):
        Customer.objects.create(
            name="Mekdes Abebe",
            company_name="Mekdes Auto Parts",
            tin_number="TIN-7788",
            phone="0911778899",
            email="mekdes@example.com",
        )
        Customer.objects.create(name="Other Customer", tin_number="TIN-1122")

        for query in ("Mekdes", "Auto Parts", "TIN-7788", "0911778899", "mekdes@example.com"):
            with self.subTest(query=query):
                response = self.client.get(reverse("customer_list"), {"q": query})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["page"].paginator.count, 1)
                self.assertContains(response, "Mekdes Auto Parts")
                self.assertNotContains(response, "Other Customer")

    def test_customer_list_is_paginated_and_shows_company_contact_correctly(self):
        company_customer = Customer.objects.create(
            name="Contact Person",
            company_name="Parts Company",
            tin_number="TIN-9000",
        )
        for index in range(26):
            Customer.objects.create(name=f"Customer {index:02d}")

        response = self.client.get(reverse("customer_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page"].paginator.count, 27)
        self.assertEqual(len(response.context["customers"]), 25)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "Parts Company")
        self.assertContains(response, "Contact Person")
        self.assertContains(response, reverse("customer_detail", args=[company_customer.pk]))


class POSChassisSearchTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="salesuser", password="pass")
        self.client.force_login(self.user)

        make = CarMake.objects.create(name="SaleMake")
        self.cm = CarModel.objects.create(
            make=make,
            name="SaleModel",
            chassis_prefixes="ZZZ",
        )
        self.prod = Product.objects.create(
            name="SalesWidget",
            selling_price=5.0,
            quantity=10,
        )
        self.prod.compatibilities.add(self.cm)

    def test_pos_search_by_chassis(self):
        url = reverse("pos")
        resp = self.client.get(url, {"q": "ZZZ"})
        self.assertEqual(resp.status_code, 200)
        products = resp.context["products"]
        self.assertIn(self.prod, products)

    def test_sale_records_customer(self):
        cust = Customer.objects.create(name="Alice")
        sale = Sale.objects.create(customer=cust, total_amount=0)
        self.assertEqual(sale.customer, cust)

    def test_pos_frontpage_and_single_sell(self):
        # front page shows both sell and add-to-cart
        p = self.prod
        url = reverse("pos")
        resp = self.client.get(url)
        self.assertContains(resp, reverse("add_to_cart", args=[p.id]))
        self.assertContains(resp, reverse("pos_single", args=[p.id]))

        # using pos_single should add item to cart; page should not show customer/payment
        single_url = reverse("pos_single", args=[p.id])
        resp = self.client.get(single_url)
        self.assertNotContains(resp, "Customer:")
        self.assertNotContains(resp, "Payment")
        self.assertNotContains(resp, "Complete")
        resp = self.client.post(single_url, {"qty": "2", "price": "20"})
        self.assertIn(resp.status_code, [200, 302])
        cart_url = reverse("cart")
        resp = self.client.get(cart_url)
        self.assertContains(resp, p.name)
        # checkout from cart
        resp = self.client.post(cart_url, {
            f"qty_{p.id}": "2",
            f"price_{p.id}": "20",
            "customer_type": "new",
            "new_name": "Eve",
            "new_phone": "999",
            "payment_method": "CASH",
        })
        self.assertIn(resp.status_code, [200, 302])

    def test_invoice_shows_customer(self):
        cust = Customer.objects.create(name="Charlie")
        sale = Sale.objects.create(customer=cust, total_amount=0, payment_method="CASH")
        item = SaleItem.objects.create(sale=sale, product=self.prod, quantity=1, price=5, cost_price=3)
        url = reverse("invoice", args=[sale.id])
        resp = self.client.get(url)
        self.assertContains(resp, "Charlie")

    def test_cart_add_and_checkout(self):
        # add product to cart, then checkout with new customer
        p = self.prod
        add_url = reverse("add_to_cart", args=[p.id])
        resp = self.client.get(add_url)
        self.assertIn(resp.status_code, [200, 302])
        cart_url = reverse("cart")
        resp = self.client.get(cart_url)
        self.assertContains(resp, p.name)
        # post checkout
        resp = self.client.post(cart_url, {
            f"qty_{p.id}": "3",
            f"price_{p.id}": "10",
            "customer_type": "new",
            "new_name": "Dave",
            "new_phone": "555",
            "payment_method": "CASH",
        })
        self.assertIn(resp.status_code, [200, 302])
