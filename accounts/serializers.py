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

    
