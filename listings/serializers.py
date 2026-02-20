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
        ]

    def get_primary_image(self, obj):
        img = next((i for i in obj.images.all() if i.is_primary), None)
        if not img:
            img = obj.images.first()
        return ListingImageSerializer(img).data if img else None


class WasteListingDetailSerializer(serializers.ModelSerializer):
    farmer_username = serializers.CharField(source="farmer.username", read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)

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
        ]
        read_only_fields = ["id", "farmer", "created_at"]


class WasteListingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteListing
        fields = ["id", "waste_type", "quantity", "unit", "location", "price", "notes", "status"]
        read_only_fields = ["id"]

    def validate_status(self, value):
        # Optional: restrict status updates (simple rule for now)
        return value
