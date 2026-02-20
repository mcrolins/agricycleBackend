from rest_framework import serializers
from .models import WasteRequest, RequestMessage
from listings.models import WasteListing


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

        # ✅ Allow requests ONLY when listing is OPEN or REQUESTED
        if listing.status in [
            WasteListing.Status.ACCEPTED,
            WasteListing.Status.COMPLETED,
            WasteListing.Status.CANCELLED,
        ]:
            raise serializers.ValidationError(
                "This listing is not available for requests."
            )

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

    class Meta:
        model = WasteRequest
        fields = [
            "id",
            "listing",
            "listing_waste_type",
            "listing_location",
            "processor",
            "processor_username",
            "quantity_requested",
            "proposed_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["processor", "status", "created_at"]


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
        read_only_fields = ["sender", "created_at"]
