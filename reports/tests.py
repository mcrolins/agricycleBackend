from datetime import datetime, timezone
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from listings.models import WasteListing
from orders.models import WasteRequest


User = get_user_model()


class ReportsApiTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.farmer = User.objects.create_user(
            username="farmer1",
            first_name="Jane",
            last_name="Farmer",
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700001001",
        )
        self.other_farmer = User.objects.create_user(
            username="farmer2",
            first_name="John",
            last_name="Doe",
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700001002",
        )
        self.processor = User.objects.create_user(
            username="processor1",
            first_name="Peter",
            last_name="Processor",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700001003",
        )
        self.other_processor = User.objects.create_user(
            username="processor2",
            first_name="Paul",
            last_name="Buyer",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700001004",
        )
        self.admin = User.objects.create_user(
            username="admin1",
            first_name="Alice",
            last_name="Admin",
            password=self.password,
            role=User.Role.ADMIN,
            phone_number="+254700001005",
        )
        User.objects.filter(pk=self.farmer.pk).update(date_joined=datetime(2026, 4, 10, 8, 0, tzinfo=timezone.utc))
        User.objects.filter(pk=self.other_farmer.pk).update(date_joined=datetime(2026, 4, 11, 8, 0, tzinfo=timezone.utc))
        User.objects.filter(pk=self.processor.pk).update(date_joined=datetime(2026, 4, 12, 8, 0, tzinfo=timezone.utc))
        User.objects.filter(pk=self.other_processor.pk).update(date_joined=datetime(2026, 4, 13, 8, 0, tzinfo=timezone.utc))
        User.objects.filter(pk=self.admin.pk).update(date_joined=datetime(2026, 4, 14, 8, 0, tzinfo=timezone.utc))
        for user in (self.farmer, self.other_farmer, self.processor, self.other_processor, self.admin):
            user.refresh_from_db()

        self.sold_listing = WasteListing.objects.create(
            farmer=self.farmer,
            waste_type="Maize stalks",
            quantity="120.00",
            unit="kg",
            location="Nakuru",
            price="800.00",
            status=WasteListing.Status.COMPLETED,
        )
        self.unsold_listing = WasteListing.objects.create(
            farmer=self.farmer,
            waste_type="Rice husks",
            quantity="60.00",
            unit="kg",
            location="Eldoret",
            price="300.00",
            status=WasteListing.Status.OPEN,
        )
        self.market_listing = WasteListing.objects.create(
            farmer=self.other_farmer,
            waste_type="Sugarcane bagasse",
            quantity="200.00",
            unit="kg",
            location="Kisumu",
            price="1000.00",
            status=WasteListing.Status.REQUESTED,
        )

        WasteRequest.objects.create(
            listing=self.sold_listing,
            processor=self.processor,
            quantity_requested="100.00",
            proposed_price="750.00",
            status=WasteRequest.Status.COMPLETED,
        )
        WasteRequest.objects.create(
            listing=self.unsold_listing,
            processor=self.other_processor,
            quantity_requested="20.00",
            proposed_price="120.00",
            status=WasteRequest.Status.PENDING,
        )
        WasteRequest.objects.create(
            listing=self.market_listing,
            processor=self.processor,
            quantity_requested="150.00",
            proposed_price="900.00",
            status=WasteRequest.Status.ACCEPTED,
        )

    def authenticate(self, user):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_farmer_reports_return_listing_sales_and_demand_metrics(self):
        self.authenticate(self.farmer)

        response = self.client.get(reverse("farmer_reports"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["revenue_earned_from_waste_sales"]["total_revenue"],
            Decimal("750"),
        )
        self.assertEqual(response.data["revenue_earned_from_waste_sales"]["total_sales"], 1)
        self.assertEqual(response.data["unsold_vs_sold_listings"]["sold"], 1)
        self.assertEqual(response.data["unsold_vs_sold_listings"]["unsold"], 1)
        self.assertEqual(response.data["most_demanded_waste_types"][0]["waste_type"], "Maize stalks")

    def test_processor_reports_return_purchase_spending_and_supplier_metrics(self):
        self.authenticate(self.processor)

        response = self.client.get(reverse("processor_reports"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["total_waste_purchased"]["total_quantity"],
            Decimal("250"),
        )
        self.assertEqual(response.data["total_waste_purchased"]["total_transactions"], 2)
        self.assertEqual(response.data["spending_trends"]["total_spend"], Decimal("1650"))
        self.assertEqual(response.data["most_reliable_suppliers"][0]["successful_transactions"], 1)
        self.assertEqual(response.data["waste_availability_trends"]["currently_available_listings"], 2)

    def test_admin_reports_require_staff_and_include_liquidity(self):
        self.authenticate(self.admin)

        response = self.client.get(reverse("admin_reports"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_platform_transactions"]["total_transactions"], 2)
        self.assertEqual(response.data["marketplace_liquidity"]["total_listings"], 3)
        self.assertEqual(response.data["marketplace_liquidity"]["sold_listings"], 2)
        self.assertEqual(len(response.data["active_users_over_time"]), 1)

    def test_non_admin_cannot_access_admin_reports(self):
        self.authenticate(self.processor)

        response = self.client.get(reverse("admin_reports"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_filters_users_by_name_and_joined_date(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard"),
            {"user_query": "Jane Farmer", "user_date_joined": "2026-04-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = list(response.context["users"])
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].username, "farmer1")
        self.assertEqual(response.context["users_total"], 1)

    def test_admin_dashboard_filters_listings_by_waste_type_and_farmer_name(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard"),
            {"listing_waste_type": "Sugarcane", "listing_user_query": "John Doe"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listings = list(response.context["listings"])
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].waste_type, "Sugarcane bagasse")
        self.assertEqual(listings[0].farmer.username, "farmer2")
        self.assertEqual(response.context["listings_total"], 1)

    def test_admin_users_csv_respects_name_and_joined_date_filters(self):
        self.authenticate(self.admin)

        response = self.client.get(
            reverse("admin_users_csv"),
            {"user_query": "Jane Farmer", "user_date_joined": "2026-04-10"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn("farmer1", content)
        self.assertNotIn("farmer2", content)

    def test_admin_listings_csv_respects_waste_type_and_farmer_filters(self):
        self.authenticate(self.admin)

        response = self.client.get(
            reverse("admin_listings_csv"),
            {"listing_waste_type": "Sugarcane", "listing_user_query": "John Doe"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn("Sugarcane bagasse", content)
        self.assertIn("farmer2", content)
        self.assertNotIn("Maize stalks", content)

    def test_admin_dashboard_filters_users_by_location(self):
        """Users with listings/orders in a given location should be returned."""
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard"),
            {"user_location": "Nakuru"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u.username for u in response.context["users"]]
        # farmer1 has a listing in Nakuru, processor1 has an order on that listing
        self.assertIn("farmer1", usernames)
        self.assertIn("processor1", usernames)
        # farmer2 has no listings/orders in Nakuru
        self.assertNotIn("farmer2", usernames)

    def test_admin_dashboard_filters_listings_by_location(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard"),
            {"listing_location": "Kisumu"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        listings = list(response.context["listings"])
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].location, "Kisumu")
        self.assertEqual(response.context["listings_total"], 1)

    def test_admin_dashboard_filters_orders_by_location(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard"),
            {"order_location": "Eldoret"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        orders = list(response.context["orders"])
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].listing.location, "Eldoret")
        self.assertEqual(response.context["orders_total"], 1)

    def test_admin_dashboard_passes_all_locations_to_context(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_locations = response.context["all_locations"]
        self.assertIn("Nakuru", all_locations)
        self.assertIn("Eldoret", all_locations)
        self.assertIn("Kisumu", all_locations)
        self.assertEqual(len(all_locations), 3)

    def test_admin_listings_csv_respects_location_filter(self):
        self.authenticate(self.admin)

        response = self.client.get(
            reverse("admin_listings_csv"),
            {"listing_location": "Nakuru"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn("Maize stalks", content)
        self.assertIn("Nakuru", content)
        self.assertNotIn("Kisumu", content)

    def test_admin_orders_csv_respects_location_filter(self):
        self.authenticate(self.admin)

        response = self.client.get(
            reverse("admin_orders_csv"),
            {"order_location": "Nakuru"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn("Nakuru", content)
        self.assertNotIn("Eldoret", content)
