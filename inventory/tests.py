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
        # performing a GET with a matching chassis prefix query should return the product
        url = reverse("product_list")
        response = self.client.get(url, {"q": "ABC"})
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


class PurchaseAddViewTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="purchaser", password="pass")
        self.client.force_login(self.user)
        self.supplier = Supplier.objects.create(name="Global Auto Parts")
        self.warehouse = Warehouse.objects.create(name="Central Warehouse")
        self.existing_product = Product.objects.create(
            name="Filter Element",
            sku="FLT-001",
            cost_price=12.0,
            selling_price=20.0,
            quantity=5
        )

    def test_purchase_add_with_new_product(self):
        url = reverse("purchase_add")
        post_data = {
            "supplier": str(self.supplier.id),
            "warehouse": str(self.warehouse.id),
            "invoice_number": "INV-1002",
            "notes": "Urgent restock",
            "item_type[]": ["existing", "new"],
            "existing_product_id[]": [str(self.existing_product.id)],
            "existing_qty[]": ["10"],
            "existing_cost[]": ["12.50"],
            "new_name[]": ["Brake Pad Front Set"],
            "new_sku[]": ["BRK-9901"],
            "new_part_number[]": ["04465-02220"],
            "new_brand[]": ["Akebono"],
            "new_cost[]": ["25.00"],
            "new_selling_price[]": ["45.00"],
            "new_location[]": ["Shelf B-3"],
            "new_qty[]": ["8"],
        }

        resp = self.client.post(url, post_data)
        self.assertEqual(resp.status_code, 302)

        # Check existing product quantity was updated (5 + 10 = 15)
        self.existing_product.refresh_from_db()
        self.assertEqual(self.existing_product.quantity, 15)

        # Check newly created product
        new_prod = Product.objects.get(sku="BRK-9901")
        self.assertEqual(new_prod.name, "Brake Pad Front Set")
        self.assertEqual(new_prod.part_number, "04465-02220")
        self.assertEqual(new_prod.quantity, 8)
        self.assertEqual(new_prod.cost_price, 25.00)
        self.assertEqual(new_prod.selling_price, 45.00)

        # Check Purchase record
        purchase = Purchase.objects.latest("id")
        self.assertEqual(purchase.supplier, self.supplier)
        self.assertEqual(purchase.warehouse, self.warehouse)
        self.assertEqual(purchase.invoice_number, "INV-1002")
        self.assertEqual(purchase.items.count(), 2)
        # Total amount: (10 * 12.50) + (8 * 25.00) = 125 + 200 = 325.00
        self.assertEqual(purchase.total_amount, 325.00)


class PartsAnalysisTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(username="parts-analyst", password="test-pass")
        self.client.force_login(self.user)
        self.product = Product.objects.create(
            name="Oil Filter",
            part_number="OF-100",
            cost_price=10,
            selling_price=20,
            quantity=5,
        )

    def test_analysis_page_displays_current_stock_summary(self):
        response = self.client.get(reverse("parts_analysis"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parts bought and sold")
        self.assertContains(response, "Oil Filter")

    def test_purchase_from_receipt_text_records_source_and_adds_stock(self):
        response = self.client.post(reverse("parts_analysis"), {
            "entry_type": "purchase",
            "reference": "SUP-77",
            "document_date": "2026-10-13",
            "party_name": "Parts Supplier",
            "source_text": "Oil Filter x 4 at 12 ETB",
            "product_id[]": [str(self.product.id)],
            "quantity[]": ["4"],
            "unit_price[]": ["12.00"],
        })

        self.assertRedirects(response, reverse("parts_analysis"))
        purchase = Purchase.objects.get(invoice_number="SUP-77")
        self.assertEqual(purchase.document_date.isoformat(), "2026-10-13")
        self.assertEqual(purchase.recorded_by, self.user)
        self.assertEqual(purchase.source_text, "Oil Filter x 4 at 12 ETB")
        self.assertEqual(purchase.total_amount, 48)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 9)

    def test_sale_from_receipt_text_records_source_and_deducts_stock(self):
        response = self.client.post(reverse("parts_analysis"), {
            "entry_type": "sale",
            "reference": "SALE-21",
            "document_date": "2026-10-14",
            "party_name": "Repair Shop",
            "source_text": "Oil Filter x 2",
            "product_id[]": [str(self.product.id)],
            "quantity[]": ["2"],
            "unit_price[]": ["23.00"],
            "payment_method": "CASH",
        })

        self.assertRedirects(response, reverse("parts_analysis"))
        from sales.models import Sale

        sale = Sale.objects.get(source_text="Oil Filter x 2")
        self.assertEqual(sale.receipt_reference, "SALE-21")
        self.assertEqual(sale.document_date.isoformat(), "2026-10-14")
        self.assertEqual(sale.total_amount, 46)
        self.assertEqual(sale.items.get().quantity, 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 3)

    def test_sale_rejects_quantity_above_stock(self):
        response = self.client.post(reverse("parts_analysis"), {
            "entry_type": "sale",
            "reference": "SALE-22",
            "document_date": "2026-10-14",
            "source_text": "Oil Filter x 8",
            "product_id[]": [str(self.product.id)],
            "quantity[]": ["8"],
            "unit_price[]": ["23.00"],
            "payment_method": "CASH",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["errors"] == [])
        self.assertFalse(Purchase.objects.exists())
        from sales.models import Sale

        self.assertFalse(Sale.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 5)

    def test_audit_date_filter_shows_matching_purchase_and_receipt(self):
        response = self.client.post(reverse("parts_analysis"), {
            "entry_type": "purchase",
            "reference": "SUP-AUDIT-1",
            "document_date": "2026-10-13",
            "party_name": "Audited Supplier",
            "source_text": "Oil Filter x 1",
            "product_id[]": [str(self.product.id)],
            "quantity[]": ["1"],
            "unit_price[]": ["10.00"],
        })
        self.assertEqual(response.status_code, 302)

        response = self.client.get(reverse("parts_analysis"), {
            "date_from": "2026-10-13",
            "date_to": "2026-10-13",
            "q": "SUP-AUDIT-1",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["recent_purchases"]), 1)
        self.assertEqual(response.context["recent_purchases"][0].invoice_number, "SUP-AUDIT-1")
        self.assertEqual(len(response.context["recent_sales"]), 0)

    def test_audit_receipts_are_paginated_without_dropping_older_rows(self):
        from datetime import date

        Purchase.objects.bulk_create([
            Purchase(invoice_number=f"AUDIT-{index}", document_date=date(2026, 10, index))
            for index in range(1, 28)
        ])

        response = self.client.get(reverse("parts_analysis"), {"purchase_page": "2"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["recent_purchases"].paginator.count, 27)
        self.assertEqual(len(response.context["recent_purchases"]), 2)
