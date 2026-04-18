from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.db.models import Q
from django.utils.dateparse import parse_date
from reports.permissions import IsPlatformAdmin
from .serializers import RegisterSerializer, UserAdminSerializer, CustomTokenObtainPairSerializer
from .models import User


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_205_RESET_CONTENT)


class PlatformAdminUserListView(generics.ListAPIView):
    """
    Platform admin view to list all users.
    """
    serializer_class = UserAdminSerializer
    permission_classes = [IsPlatformAdmin]
    
    def get_queryset(self):
        users = User.objects.all().order_by("-date_joined")
        query = self.request.query_params.get("query", "").strip()
        date_joined = self.request.query_params.get("date_joined", "").strip()

        if query:
            terms = [term.strip() for term in query.split() if term.strip()]
            for term in terms:
                users = users.filter(
                    Q(username__icontains=term)
                    | Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                )

        joined_date = parse_date(date_joined) if date_joined else None
        if joined_date:
            users = users.filter(date_joined__date=joined_date)

        return users

from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
