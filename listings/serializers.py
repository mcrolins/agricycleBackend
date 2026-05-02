# listings/serializers.py
from rest_framework import serializers
from .models import WasteListing, ListingImage
from orders.serializers import get_listing_remaining_quantity


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "is_primary", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class WasteListingListSerializer(serializers.ModelSerializer):
    farmer_username = serializers.CharField(source="farmer.username", read_only=True)
    primary_image = serializers.SerializerMethodField()
    remaining_quantity = serializers.SerializerMethodField()
    request_count = serializers.SerializerMethodField()

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
            "request_count",
        ]

    def get_remaining_quantity(self, obj):
        return get_listing_remaining_quantity(obj)

    def get_primary_image(self, obj):
        img = next((i for i in obj.images.all() if i.is_primary), None)
        if not img:
            img = obj.images.first()
        return ListingImageSerializer(img).data if img else None

    def get_request_count(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'requests' in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache['requests'])
        return obj.requests.count()


class WasteListingDetailSerializer(serializers.ModelSerializer):
    farmer_username = serializers.CharField(source="farmer.username", read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    remaining_quantity = serializers.SerializerMethodField()
    request_count = serializers.SerializerMethodField()
    bid_summary = serializers.SerializerMethodField()

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
            "request_count",
            "bid_summary",
        ]
        read_only_fields = ["id", "farmer", "created_at"]

    def get_remaining_quantity(self, obj):
        return get_listing_remaining_quantity(obj)

    def get_request_count(self, obj):
        return obj.requests.count()

    def get_bid_summary(self, obj):
        """Return summary of bids for competitive visibility."""
        from orders.models import WasteRequest
        requests = obj.requests.all()
        if not requests.exists():
            return {
                "total_bids": 0,
                "pending_bids": 0,
                "accepted_bids": 0,
                "price_range": None,
                "quantity_range": None,
            }

        pending = requests.filter(status=WasteRequest.Status.PENDING)
        accepted = requests.filter(status=WasteRequest.Status.ACCEPTED)
        all_active = requests.exclude(
            status__in=[WasteRequest.Status.REJECTED, WasteRequest.Status.CANCELLED]
        )

        prices = [r.proposed_price for r in all_active if r.proposed_price is not None]
        quantities = [r.quantity_requested for r in all_active]

        return {
            "total_bids": requests.count(),
            "pending_bids": pending.count(),
            "accepted_bids": accepted.count(),
            "price_range": {
                "min": min(prices) if prices else None,
                "max": max(prices) if prices else None,
            } if prices else None,
            "quantity_range": {
                "min": min(quantities) if quantities else None,
                "max": max(quantities) if quantities else None,
            } if quantities else None,
        }


class WasteListingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteListing
        fields = ["id", "waste_type", "quantity", "unit", "location", "price", "notes", "status"]
        read_only_fields = ["id"]

    def validate_status(self, value):
        # Optional: restrict status updates (simple rule for now)
        return value
