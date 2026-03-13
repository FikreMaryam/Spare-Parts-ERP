from django.test import TestCase
from django.urls import reverse

from .models import (
    CarMake,
    CarModel,
    Product,
    Warehouse,
    Supplier,
    Purchase,
    PurchaseItem,
    StockMovement,
)


class ChassisLookupTests(TestCase):
    def setUp(self):
        # create a user and log in so views requiring authentication succeed
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.force_login(self.user)

        make = CarMake.objects.create(name="TestMake")
        # a model that should match prefixes
        self.cm = CarModel.objects.create(
            make=make,
            name="ModelX",
            chassis_prefixes="ABC, 123",
        )
        self.product = Product.objects.create(
            name="Widget",
            selling_price=10.0,
        )
        self.product.compatibilities.add(self.cm)

    def test_matches_chassis_prefix(self):
        # should match when the chassis starts with a listed prefix
        self.assertTrue(self.cm.matches_chassis("ABC9999"))
        self.assertTrue(self.cm.matches_chassis("123456"))
        # case insensitive and trimmed
        self.assertTrue(self.cm.matches_chassis(" abc000"))
        # non-matching value
        self.assertFalse(self.cm.matches_chassis("XYZ000"))
        # empty or None should be false
        self.assertFalse(self.cm.matches_chassis(""))
        self.assertFalse(self.cm.matches_chassis(None))

    def test_search_products_by_chassis(self):
        # performing a GET with a chassis number should return the product
        url = reverse("product_list")
        response = self.client.get(url, {"q": "ABC999"})
        self.assertEqual(response.status_code, 200)
        products = response.context["page"].object_list
        self.assertIn(self.product, products)
        # search with non-matching chassis should yield no results
        response = self.client.get(url, {"q": "XYZ"})
        products = response.context["page"].object_list
        self.assertNotIn(self.product, products)


class StockMovementTests(TestCase):
    def setUp(self):
        self.warehouse = Warehouse.objects.create(name="Main")
        self.product = Product.objects.create(name="Item", selling_price=5.0)
        self.supplier = Supplier.objects.create(name="Sup1")
        self.purchase = Purchase.objects.create(supplier=self.supplier, warehouse=self.warehouse)

    def test_purchase_creates_stock_movement(self):
        PurchaseItem.objects.create(purchase=self.purchase, product=self.product, quantity=10, unit_cost=2.0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 10)
        move = StockMovement.objects.filter(product=self.product).first()
        self.assertIsNotNone(move)
        self.assertEqual(move.movement_type, "purchase")
        self.assertEqual(move.quantity, 10)
        self.assertEqual(move.warehouse, self.warehouse)

    def test_sale_decreases_and_logs(self):
        # create stock then a sale item
        PurchaseItem.objects.create(purchase=self.purchase, product=self.product, quantity=5, unit_cost=1.0)
        from sales.models import Sale, SaleItem
        sale = Sale.objects.create(total_amount=0)
        SaleItem.objects.create(sale=sale, product=self.product, quantity=3, price=10, cost_price=1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 2)
        move = StockMovement.objects.filter(product=self.product, movement_type="sale").first()
        self.assertIsNotNone(move)
        self.assertEqual(move.quantity, -3)
