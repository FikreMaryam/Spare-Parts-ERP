from django.test import TestCase
from django.urls import reverse

from inventory.models import CarMake, CarModel, Product
from .models import Customer


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
        )
        self.prod.compatibilities.add(self.cm)

    def test_pos_search_by_chassis(self):
        url = reverse("pos")
        resp = self.client.get(url, {"q": "ZZZ123"})
        self.assertEqual(resp.status_code, 200)
        products = resp.context["products"]
        self.assertIn(self.prod, products)

    def test_sale_records_customer(self):
        cust = Customer.objects.create(name="Alice")
        from .models import Sale
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
        self.assertEqual(resp.status_code, 302)
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
        self.assertEqual(resp.status_code, 302)
        sale = Sale.objects.last()
        self.assertEqual(sale.items.first().quantity, 2)

    def test_invoice_shows_customer(self):
        cust = Customer.objects.create(name="Charlie")
        sale = Sale.objects.create(customer=cust, total_amount=0, payment_method="CASH")
        from .models import SaleItem
        item = SaleItem.objects.create(sale=sale, product=self.prod, quantity=1, price=5, cost_price=3)
        url = reverse("invoice", sale.id)
        resp = self.client.get(url)
        self.assertContains(resp, "Charlie")

    def test_cart_add_and_checkout(self):
        # add product to cart, then checkout with new customer
        p = self.prod
        add_url = reverse("add_to_cart", args=[p.id])
        resp = self.client.get(add_url)
        self.assertEqual(resp.status_code, 302)
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
        self.assertEqual(resp.status_code, 302)
        sale = Sale.objects.last()
        self.assertEqual(sale.customer.name, "Dave")
        self.assertEqual(sale.items.first().quantity, 3)
