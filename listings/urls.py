# listings/urls.py
from django.urls import path
from .views import (
    WasteListingListCreateView,
    WasteListingDetailView,
    ListingImageUploadView,
    ListingImageDeleteView,
    ListingImageSetPrimaryView,
)

urlpatterns = [
    path("", WasteListingListCreateView.as_view(), name="listing-list-create"),
    path("<int:pk>/", WasteListingDetailView.as_view(), name="listing-detail"),
    path("<int:pk>/images/", ListingImageUploadView.as_view(), name="listing-image-upload"),
    path("<int:pk>/images/<int:image_id>/", ListingImageDeleteView.as_view(), name="listing-image-delete"),
    path("<int:pk>/images/<int:image_id>/primary/", ListingImageSetPrimaryView.as_view(), name="listing-image-primary"),
]
