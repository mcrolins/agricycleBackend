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
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700001001",
        )
        self.other_farmer = User.objects.create_user(
            username="farmer2",
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700001002",
        )
        self.processor = User.objects.create_user(
            username="processor1",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700001003",
        )
        self.other_processor = User.objects.create_user(
            username="processor2",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700001004",
        )
        self.admin = User.objects.create_user(
            username="admin1",
            password=self.password,
            role=User.Role.ADMIN,
            phone_number="+254700001005",
        )

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
