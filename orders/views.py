from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import WasteRequest, RequestMessage
from .serializers import (
    WasteRequestCreateSerializer,
    WasteRequestUpdateSerializer,
    WasteRequestSerializer,
    RequestMessageSerializer
)
from .permisions import IsProcessor, IsFarmer, IsRequestParticipant  # ✅ fixed spelling
from reports.permissions import IsPlatformAdmin
from .serializers import WasteRequestSerializer
from listings.models import WasteListing


class RequestCreateView(generics.CreateAPIView):
    serializer_class = WasteRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsProcessor]

    def perform_create(self, serializer):
        listing = serializer.validated_data["listing"]

        # Prevent requesting your own listing
        if listing.farmer_id == self.request.user.id:
            raise ValidationError("You cannot request your own listing.")

        # ✅ Block requests if listing is not available
        if listing.status in [
            WasteListing.Status.COMPLETED,
            WasteListing.Status.CANCELLED,
        ]:
            raise ValidationError("This listing is not available for requests.")

        # ✅ OPEN -> REQUESTED when first request comes in
        if listing.status == WasteListing.Status.OPEN:
            listing.status = WasteListing.Status.REQUESTED
            listing.save(update_fields=["status"])

        serializer.save(processor=self.request.user)


class MyRequestsView(generics.ListAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsProcessor]

    def get_queryset(self):
        return WasteRequest.objects.select_related("listing", "processor").filter(processor=self.request.user)


class MyRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WasteRequest.objects.select_related("listing", "processor", "listing__farmer")
    permission_classes = [permissions.IsAuthenticated, IsProcessor]

    def get_queryset(self):
        return self.queryset.filter(processor=self.request.user)

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return WasteRequestUpdateSerializer
        return WasteRequestSerializer

    def _get_owned_request(self):
        return self.get_object()

    def perform_update(self, serializer):
        wr = self._get_owned_request()
        if wr.status != WasteRequest.Status.PENDING:
            raise ValidationError("Only pending requests can be edited.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        wr = self._get_owned_request()

        if wr.status != WasteRequest.Status.PENDING:
            raise ValidationError("Only pending requests can be deleted.")

        listing = wr.listing
        wr.delete()

        has_pending = WasteRequest.objects.filter(
            listing_id=listing.id,
            status=WasteRequest.Status.PENDING,
        ).exists()

        listing.status = WasteListing.Status.REQUESTED if has_pending else WasteListing.Status.OPEN
        listing.save(update_fields=["status"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class IncomingRequestsView(generics.ListAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsFarmer]

    def get_queryset(self):
        return WasteRequest.objects.select_related("listing", "processor").filter(listing__farmer=self.request.user)


class RequestStatusUpdateView(generics.UpdateAPIView):
    queryset = WasteRequest.objects.select_related("listing", "processor", "listing__farmer")
    serializer_class = WasteRequestSerializer
    permission_classes = [permissions.IsAuthenticated, IsRequestParticipant]

    def patch(self, request, *args, **kwargs):
        wr: WasteRequest = self.get_object()
        new_status = request.data.get("status")

        allowed_statuses = [
            WasteRequest.Status.ACCEPTED,
            WasteRequest.Status.REJECTED,
            WasteRequest.Status.CANCELLED,
            WasteRequest.Status.COMPLETED,
        ]
        if new_status not in allowed_statuses:
            raise ValidationError({"status": "Invalid status."})

        user = request.user

        # Farmer can accept/reject/complete
        if new_status in [
            WasteRequest.Status.ACCEPTED,
            WasteRequest.Status.REJECTED,
            WasteRequest.Status.COMPLETED,
        ]:
            if wr.listing.farmer_id != user.id:
                raise PermissionDenied("Only the listing owner can do that.")

        # Processor can cancel
        if new_status == WasteRequest.Status.CANCELLED:
            if wr.processor_id != user.id:
                raise PermissionDenied("Only the processor can cancel their request.")

        # Basic state protection
        if wr.status in [
            WasteRequest.Status.REJECTED,
            WasteRequest.Status.CANCELLED,
            WasteRequest.Status.COMPLETED,
        ]:
            raise ValidationError("This request is already closed.")

        # Partial accept: subtract quantity, re-open if remainder >0 (atomic)
        if new_status == WasteRequest.Status.ACCEPTED:
            from decimal import Decimal
            with transaction.atomic():
                wr.status = WasteRequest.Status.ACCEPTED
                wr.save(update_fields=["status"])

                listing = wr.listing
                original_quantity = listing.quantity
                total_accepted = sum(
                    r.quantity_requested for r in listing.requests.filter(status=WasteRequest.Status.ACCEPTED)
                )
                listing.quantity = max(Decimal('0.00'), original_quantity - total_accepted)
                listing.status = WasteListing.Status.COMPLETED if listing.quantity <= 0 else WasteListing.Status.OPEN
                listing.save(update_fields=["quantity", "status"])

                # Auto-reject other pending requests for same listing
                WasteRequest.objects.filter(
                    listing_id=wr.listing_id,
                    status=WasteRequest.Status.PENDING
                ).exclude(id=wr.id).update(status=WasteRequest.Status.REJECTED)

            return Response(WasteRequestSerializer(wr).data)

        # Other status changes
        wr.status = new_status
        wr.save(update_fields=["status"])

        # If rejected/cancelled: listing stays REQUESTED if pending exists else OPEN
        if new_status in [WasteRequest.Status.REJECTED, WasteRequest.Status.CANCELLED]:
            has_pending = WasteRequest.objects.filter(
                listing_id=wr.listing_id,
                status=WasteRequest.Status.PENDING
            ).exists()

            wr.listing.status = WasteListing.Status.REQUESTED if has_pending else WasteListing.Status.OPEN
            wr.listing.save(update_fields=["status"])

        # If completed, mark listing completed too
        if new_status == WasteRequest.Status.COMPLETED:
            wr.listing.status = WasteListing.Status.COMPLETED
            wr.listing.save(update_fields=["status"])

        return Response(WasteRequestSerializer(wr).data)


class RequestContactInfoView(generics.RetrieveAPIView):
    queryset = WasteRequest.objects.select_related("processor", "listing__farmer")
    permission_classes = [permissions.IsAuthenticated, IsRequestParticipant]

    def retrieve(self, request, *args, **kwargs):
        wr: WasteRequest = self.get_object()

        if wr.status != WasteRequest.Status.ACCEPTED:
            raise PermissionDenied("Contact details are only available after acceptance.")

        farmer = wr.listing.farmer
        processor = wr.processor

        return Response({
            "request_id": wr.id,
            "listing_id": wr.listing_id,
            "farmer": {
                "name": (farmer.full_name if getattr(farmer, "full_name", "") else farmer.username),
                "phone_number": farmer.phone_number,
            },
            "processor": {
                "name": (processor.full_name if getattr(processor, "full_name", "") else processor.username),
                "phone_number": processor.phone_number,
            },
        })


class RequestMessageListCreateView(generics.ListCreateAPIView):
    serializer_class = RequestMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        request_id = self.kwargs["pk"]
        wr = get_object_or_404(
            WasteRequest.objects.select_related("listing__farmer"),
            pk=request_id,
        )

        # Only participants can see messages
        if not (wr.processor_id == self.request.user.id or wr.listing.farmer_id == self.request.user.id):
            raise PermissionDenied("Not allowed.")
        return RequestMessage.objects.filter(request_id=request_id).select_related("sender")

    def perform_create(self, serializer):
        request_id = self.kwargs["pk"]
        wr = get_object_or_404(
            WasteRequest.objects.select_related("listing__farmer"),
            pk=request_id,
        )

        # Only participants can send messages
        if not (wr.processor_id == self.request.user.id or wr.listing.farmer_id == self.request.user.id):
            raise PermissionDenied("Not allowed.")

        serializer.save(request=wr, sender=self.request.user)


class AdminRequestsView(generics.ListAPIView):
    """
    Platform admin overview of all waste requests.
    """
    serializer_class = WasteRequestSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        from django.db.models import Count
        return WasteRequest.objects.select_related(
            'listing__farmer', 'processor', 'listing'
        ).prefetch_related('messages').annotate(
            message_count=Count('messages')
        ).order_by('-created_at')
