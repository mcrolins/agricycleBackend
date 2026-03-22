from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthSecurityTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username="processor1",
            password=self.password,
            role=User.Role.PROCESSOR,
            phone_number="+254700000001",
        )

    def authenticate(self):
        token_response = self.client.post(
            reverse("token_obtain_pair"),
            {"username": self.user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        access = token_response.data["access"]
        refresh = token_response.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return access, refresh

    def test_logout_blacklists_refresh_token(self):
        _, refresh = self.authenticate()

        logout_response = self.client.post(
            reverse("logout"),
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(
            reverse("token_refresh"),
            {"refresh": refresh},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_api_response_is_not_cacheable(self):
        self.authenticate()

        response = self.client.get(reverse("my_requests"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")
