from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import BusinessProfile


class ShopDisplayNameTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="shop-name-editor",
            password="test-password",
        )
        self.client.force_login(user)
        self.profile = BusinessProfile.objects.create(
            name="Registered Legal Name",
            trade_name="Old Shop Name",
        )

    def test_shop_display_name_is_used_throughout_the_app(self):
        response = self.client.get(reverse("reports_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["app_name"], "Old Shop Name")
        self.assertContains(response, "Shop Display Name")

    def test_saving_shop_display_name_updates_shared_app_name(self):
        response = self.client.post(
            reverse("reports_settings"),
            {
                "name": "Registered Legal Name",
                "trade_name": "New Shop Name",
                "tin_number": "",
                "currency_code": "ETB",
                "vat_rate_percent": "15",
                "phone": "",
                "email": "",
                "address": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.name, "Registered Legal Name")
        self.assertEqual(self.profile.trade_name, "New Shop Name")
        self.assertEqual(response.context["app_name"], "New Shop Name")
        self.assertContains(response, "New Shop Name")
