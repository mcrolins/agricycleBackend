from rest_framework import serializers
from django.db import IntegrityError
from .models import User

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

