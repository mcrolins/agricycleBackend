from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from listings.models import WasteListing
from orders.models import RequestMessage, WasteRequest


User = get_user_model()


class OrdersWorkflowTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.farmer = User.objects.create_user(
            username="farmer1",
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700000010",
        )
        self.processor = User.objects.create_user(
            username="processor1",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700000011",
        )
        self.other_processor = User.objects.create_user(
            username="processor2",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700000012",
        )
        self.listing = WasteListing.objects.create(
            farmer=self.farmer,
            waste_type="Maize stalks",
            quantity="100.00",
            unit="kg",
            location="Nakuru",
            price="500.00",
            notes="Dry stock",
        )

    def authenticate(self, user):
        response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    def create_request(self, user=None, quantity="25.00", price="200.00"):
        user = user or self.processor
        self.authenticate(user)
        response = self.client.post(
            reverse("request_create"),
            {
                "listing": self.listing.id,
                "quantity_requested": quantity,
                "proposed_price": price,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def test_processor_can_create_update_and_delete_own_pending_request(self):
        create_response = self.create_request()
        request_id = create_response.data["id"]

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, WasteListing.Status.REQUESTED)

        update_response = self.client.patch(
            reverse("my_request_detail", args=[request_id]),
            {"quantity_requested": "40.00", "proposed_price": "300.00"},
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        waste_request = WasteRequest.objects.get(pk=request_id)
        self.assertEqual(str(waste_request.quantity_requested), "40.00")
        self.assertEqual(str(waste_request.proposed_price), "300.00")

        delete_response = self.client.delete(reverse("my_request_detail", args=[request_id]))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WasteRequest.objects.filter(pk=request_id).exists())

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, WasteListing.Status.OPEN)

    def test_farmer_accepting_request_rejects_others_and_unlocks_contact(self):
        first = self.create_request(self.processor)
        self.client.credentials()
        second = self.create_request(self.other_processor, quantity="30.00", price="250.00")

        self.authenticate(self.farmer)
        accept_response = self.client.patch(
            reverse("request_status", args=[first.data["id"]]),
            {"status": WasteRequest.Status.ACCEPTED},
            format="json",
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)

        accepted = WasteRequest.objects.get(pk=first.data["id"])
        rejected = WasteRequest.objects.get(pk=second.data["id"])
        self.assertEqual(accepted.status, WasteRequest.Status.ACCEPTED)
        self.assertEqual(rejected.status, WasteRequest.Status.REJECTED)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, WasteListing.Status.ACCEPTED)

        contact_response = self.client.get(reverse("request_contact", args=[first.data["id"]]))
        self.assertEqual(contact_response.status_code, status.HTTP_200_OK)
        self.assertEqual(contact_response.data["farmer"]["phone_number"], self.farmer.phone_number)
        self.assertEqual(contact_response.data["processor"]["phone_number"], self.processor.phone_number)

    def test_contact_info_requires_accepted_request(self):
        create_response = self.create_request()

        self.authenticate(self.processor)
        response = self.client.get(reverse("request_contact", args=[create_response.data["id"]]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_participants_can_message_request(self):
        create_response = self.create_request()
        request_id = create_response.data["id"]

        self.authenticate(self.processor)
        post_response = self.client.post(
            reverse("request_messages", args=[request_id]),
            {"text": "Can you confirm pickup time?"},
            format="json",
        )
        self.assertEqual(post_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RequestMessage.objects.filter(request_id=request_id).count(), 1)

        self.authenticate(self.farmer)
        list_response = self.client.get(reverse("request_messages", args=[request_id]))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        outsider = User.objects.create_user(
            username="farmer2",
            password=self.password,
            role=User.Role.FARMER,
            phone_number="+254700000013",
        )
        self.authenticate(outsider)
        forbidden_response = self.client.get(reverse("request_messages", args=[request_id]))
        self.assertEqual(forbidden_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_owner_can_edit_pending_request(self):
        create_response = self.create_request()
        request_id = create_response.data["id"]

        self.authenticate(self.other_processor)
        response = self.client.patch(
            reverse("my_request_detail", args=[request_id]),
            {"quantity_requested": "60.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
