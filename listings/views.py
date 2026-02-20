# listings/views.py
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import WasteListing, ListingImage
from .serializers import (
    ListingImageSerializer,
    WasteListingCreateUpdateSerializer,
    WasteListingDetailSerializer,
    WasteListingListSerializer,
)
from .permissions import IsFarmer, IsOwnerOrReadOnly


class WasteListingListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = (
            WasteListing.objects
            .select_related("farmer")
            .prefetch_related("images")
            .order_by("-created_at")
        )

        status_q = self.request.query_params.get("status")
        location_q = self.request.query_params.get("location")
        waste_type_q = self.request.query_params.get("waste_type")

        if status_q:
            qs = qs.filter(status=status_q)
        if location_q:
            qs = qs.filter(location__icontains=location_q)
        if waste_type_q:
            qs = qs.filter(waste_type__icontains=waste_type_q)

        return qs

    def get_serializer_class(self):
        return WasteListingCreateUpdateSerializer if self.request.method == "POST" else WasteListingListSerializer

    def perform_create(self, serializer):
        if not (self.request.user.is_authenticated and getattr(self.request.user, "role", None) == "FARMER"):
            raise PermissionDenied("Only FARMER users can create listings.")
        serializer.save(farmer=self.request.user)


class WasteListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WasteListing.objects.select_related("farmer").prefetch_related("images")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        return WasteListingCreateUpdateSerializer if self.request.method in ("PUT", "PATCH") else WasteListingDetailSerializer


class ListingImageUploadView(generics.CreateAPIView):
    """
    POST /api/v1/listings/<id>/images/
    multipart/form-data:
      - image: <file>  (required)
      - is_primary: true|false (optional)
    """
    serializer_class = ListingImageSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def create(self, request, *args, **kwargs):
        listing = get_object_or_404(WasteListing, pk=kwargs["pk"])

        if listing.farmer_id != request.user.id:
            return Response({"detail": "You can only upload images to your own listings."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        is_primary = serializer.validated_data.get("is_primary", False)

        with transaction.atomic():
            if is_primary:
                ListingImage.objects.filter(listing=listing, is_primary=True).update(is_primary=False)

            img = ListingImage.objects.create(listing=listing, **serializer.validated_data)

        return Response(ListingImageSerializer(img).data, status=status.HTTP_201_CREATED)


class ListingImageDeleteView(generics.DestroyAPIView):
    """
    DELETE /api/v1/listings/<id>/images/<image_id>/
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def delete(self, request, *args, **kwargs):
        listing = get_object_or_404(WasteListing, pk=kwargs["pk"])
        img = get_object_or_404(ListingImage, pk=kwargs["image_id"], listing=listing)

        if listing.farmer_id != request.user.id:
            return Response({"detail": "You can only delete images from your own listings."}, status=403)

        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ListingImageSetPrimaryView(generics.UpdateAPIView):
    """
    PATCH /api/v1/listings/<id>/images/<image_id>/primary/
    """
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def patch(self, request, *args, **kwargs):
        listing = get_object_or_404(WasteListing, pk=kwargs["pk"])
        img = get_object_or_404(ListingImage, pk=kwargs["image_id"], listing=listing)

        if listing.farmer_id != request.user.id:
            return Response({"detail": "You can only update images on your own listings."}, status=403)

        with transaction.atomic():
            ListingImage.objects.filter(listing=listing, is_primary=True).update(is_primary=False)
            img.is_primary = True
            img.save(update_fields=["is_primary"])

        return Response(ListingImageSerializer(img).data, status=status.HTTP_200_OK)
