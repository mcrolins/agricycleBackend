# listings/serializers.py
from rest_framework import serializers
from .models import WasteListing, ListingImage


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "is_primary", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class WasteListingListSerializer(serializers.ModelSerializer):
    farmer_username = serializers.CharField(source="farmer.username", read_only=True)
    primary_image = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = WasteListing
        fields = [
            "id",
            "waste_type",
            "quantity",
            "unit",
            "location",
            "price",
            "status",
            "created_at",
            "farmer_username",
            "primary_image",
            "remaining_quantity",
        ]

    def get_remaining_quantity(self, obj):
        from decimal import Decimal
        from orders.models import WasteRequest
        total_accepted = sum(
            r.quantity_requested for r in obj.requests.filter(status=WasteRequest.Status.ACCEPTED)
        )
        return max(Decimal("0.00"), obj.quantity - total_accepted)

    def get_primary_image(self, obj):
        img = next((i for i in obj.images.all() if i.is_primary), None)
        if not img:
            img = obj.images.first()
        return ListingImageSerializer(img).data if img else None


class WasteListingDetailSerializer(serializers.ModelSerializer):
    farmer_username = serializers.CharField(source="farmer.username", read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    remaining_quantity = serializers.SerializerMethodField()

    class Meta:
        model = WasteListing
        fields = [
            "id",
            "farmer",
            "farmer_username",
            "waste_type",
            "quantity",
            "unit",
            "location",
            "price",
            "notes",
            "status",
            "created_at",
            "images",
            "remaining_quantity",
        ]
        read_only_fields = ["id", "farmer", "created_at"]

    def get_remaining_quantity(self, obj):
        from decimal import Decimal
        from orders.models import WasteRequest
        total_accepted = sum(
            r.quantity_requested for r in obj.requests.filter(status=WasteRequest.Status.ACCEPTED)
        )
        return max(Decimal("0.00"), obj.quantity - total_accepted)


class WasteListingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteListing
        fields = ["id", "waste_type", "quantity", "unit", "location", "price", "notes", "status"]
        read_only_fields = ["id"]

    def validate_status(self, value):
        # Optional: restrict status updates (simple rule for now)
        return value
