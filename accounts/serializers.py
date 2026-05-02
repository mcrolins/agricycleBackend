from rest_framework import serializers
from django.db import IntegrityError
from .models import User, Review, Complaint
from listings.models import WasteListing

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.ReadOnlyField(source='reviewer.full_name')
    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'reviewer_name', 'reviewee', 'request_id', 'rating', 'comment', 'created_at']
        read_only_fields = ['reviewer']

class ComplaintSerializer(serializers.ModelSerializer):
    reporter_name = serializers.ReadOnlyField(source='reporter.full_name')
    class Meta:
        model = Complaint
        fields = ['id', 'reporter', 'reporter_name', 'reported', 'description', 'created_at']
        read_only_fields = ['reporter']

class UserMinimalSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']

class ComplaintAdminSerializer(serializers.ModelSerializer):
    reporter = UserMinimalSerializer(read_only=True)
    reported = UserMinimalSerializer(read_only=True)
    class Meta:
        model = Complaint
        fields = ['id', 'reporter', 'reported', 'description', 'created_at']

class FarmerProfileSerializer(serializers.ModelSerializer):
    total_listings = serializers.SerializerMethodField()
    accepted_listings = serializers.SerializerMethodField()
    listings = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    complaints = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'total_listings', 'accepted_listings', 'listings', 'reviews', 'complaints', 'average_rating']

    def get_total_listings(self, obj):
        return WasteListing.objects.filter(farmer=obj).count()

    def get_accepted_listings(self, obj):
        return WasteListing.objects.filter(farmer=obj, status__in=['ACCEPTED', 'COMPLETED']).count()

    def get_listings(self, obj):
        from listings.serializers import WasteListingListSerializer
        listings = WasteListing.objects.filter(farmer=obj).order_by('-created_at')[:10]
        return WasteListingListSerializer(listings, many=True).data

    def get_reviews(self, obj):
        reviews = obj.reviews_received.all().order_by('-created_at')
        return ReviewSerializer(reviews, many=True).data

    def get_complaints(self, obj):
        complaints = obj.complaints_received.all().order_by('-created_at')
        return ComplaintSerializer(complaints, many=True).data

    def get_average_rating(self, obj):
        reviews = obj.reviews_received.exclude(rating__isnull=True)
        if reviews.exists():
            return sum([r.rating for r in reviews]) / reviews.count()
        return None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(required=True)

    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'role', 'phone_number']
    
    def validate_phone_number(self, value):
        if value:
            v = value.strip()
            # Light validation (Kenya-friendly): starts with + or digits, min length 9
            if len(v) < 9:
                raise serializers.ValidationError("Phone number looks too short.")
            if User.objects.filter(phone_number=v).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
            return v
        return value
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            # Protect API clients from raw 500s if unique constraints are hit at DB level.
            raise serializers.ValidationError(
                {"detail": "Unable to register with provided credentials. Check username and phone number uniqueness."}
            )
        return user


class UserAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    is_platform_admin = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'first_name', 'last_name', 'email', 'role', 'phone_number', 'is_active', 'date_joined', 'is_platform_admin']

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token

