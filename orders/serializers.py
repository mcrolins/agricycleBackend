from rest_framework import serializers
from .models import WasteRequest, RequestMessage
from listings.models import WasteListing


def get_listing_remaining_quantity(listing, exclude_request_id=None):
    from decimal import Decimal

    accepted_requests = listing.requests.filter(status=WasteRequest.Status.ACCEPTED)
    if exclude_request_id is not None:
        accepted_requests = accepted_requests.exclude(id=exclude_request_id)

    total_accepted = sum((r.quantity_requested for r in accepted_requests), Decimal("0.00"))
    return max(Decimal("0.00"), listing.quantity - total_accepted)


class WasteRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteRequest
        fields = [
            "id",
            "listing",
            "quantity_requested",
            "proposed_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate(self, attrs):
        listing = attrs["listing"]
        request = self.context.get("request")

        # ✅ Allow requests when listing is OPEN, REQUESTED, or partially ACCEPTED
        if listing.status in [
            WasteListing.Status.COMPLETED,
            WasteListing.Status.CANCELLED,
        ]:
            raise serializers.ValidationError(
                "This listing is not available for requests."
            )

        if attrs["quantity_requested"] > get_listing_remaining_quantity(listing):
            raise serializers.ValidationError({
                "quantity_requested": "Requested quantity exceeds the remaining listing quantity."
            })

        return attrs


class WasteRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteRequest
        fields = ["quantity_requested", "proposed_price"]

    def validate(self, attrs):
        quantity_requested = attrs.get("quantity_requested", self.instance.quantity_requested)
        if quantity_requested > get_listing_remaining_quantity(
            self.instance.listing,
            exclude_request_id=self.instance.id,
        ):
            raise serializers.ValidationError({
                "quantity_requested": "Requested quantity exceeds the remaining listing quantity."
            })
        return attrs


class WasteRequestSerializer(serializers.ModelSerializer):
    processor_username = serializers.CharField(
        source="processor.username",
        read_only=True
    )
    listing_waste_type = serializers.CharField(
        source="listing.waste_type",
        read_only=True
    )
    listing_location = serializers.CharField(
        source="listing.location",
        read_only=True
    )
    listing_quantity = serializers.DecimalField(
        source="listing.quantity",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    listing_unit = serializers.CharField(
        source="listing.unit",
        read_only=True,
    )
    remaining_quantity = serializers.SerializerMethodField()
    total_bids = serializers.SerializerMethodField()

    class Meta:
        model = WasteRequest
        fields = [
            "id",
            "listing",
            "listing_waste_type",
            "listing_location",
            "listing_quantity",
            "listing_unit",
            "processor",
            "processor_username",
            "quantity_requested",
            "proposed_price",
            "status",
            "created_at",
            "remaining_quantity",
            "total_bids",
        ]
        read_only_fields = ["processor", "status", "created_at"]

    def get_remaining_quantity(self, obj):
        return get_listing_remaining_quantity(obj.listing)

    def get_total_bids(self, obj):
        return WasteRequest.objects.filter(listing_id=obj.listing_id).count()


class RequestMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(
        source="sender.username",
        read_only=True
    )

    class Meta:
        model = RequestMessage
        fields = [
            "id",
            "request",
            "sender",
            "sender_username",
            "text",
            "created_at",
        ]
        read_only_fields = ["request", "sender", "created_at"]
