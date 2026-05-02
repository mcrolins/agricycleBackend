from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import LogoutView, RegisterView, PlatformAdminUserListView, PlatformAdminComplaintListView, CustomTokenObtainPairView, ReviewCreateView, ComplaintCreateView, FarmerProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/users/", PlatformAdminUserListView.as_view(), name="admin_users"),
    path("admin/complaints/", PlatformAdminComplaintListView.as_view(), name="admin_complaints"),
    path("review/", ReviewCreateView.as_view(), name="review_create"),
    path("complaint/", ComplaintCreateView.as_view(), name="complaint_create"),
    path("farmer/<int:pk>/", FarmerProfileView.as_view(), name="farmer_profile"),
]
