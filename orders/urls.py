from django.urls import path
from .views import (
    RequestCreateView,
    MyRequestDetailView,
    MyRequestsView,
    IncomingRequestsView,
    RequestStatusUpdateView,
    RequestContactInfoView,
    RequestMessageListCreateView,
)

urlpatterns = [
    path("create/", RequestCreateView.as_view(), name="request_create"),
    path("mine/", MyRequestsView.as_view(), name="my_requests"),
    path("mine/<int:pk>/", MyRequestDetailView.as_view(), name="my_request_detail"),
    path("incoming/", IncomingRequestsView.as_view(), name="incoming_requests"),
    path("<int:pk>/status/", RequestStatusUpdateView.as_view(), name="request_status"),
    path("<int:pk>/contact/", RequestContactInfoView.as_view(), name="request_contact"),

    # Simple REST chat
    path("<int:pk>/messages/", RequestMessageListCreateView.as_view(), name="request_messages"),
]
