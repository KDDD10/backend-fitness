from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_no",
            "password",
            "is_staff",
        )
        extra_kwargs = {
            "email": {"required": True},
            "password": {"write_only": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "phone_no": {"required": True},
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            email=validated_data.get("email"),
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            phone_no=validated_data["phone_no"],
        )
        return user


class CustomTokenCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    token = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    phone_no = serializers.CharField(read_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid email or password")
        refresh = RefreshToken.for_user(user)
        return {
            "token": str(refresh.access_token),
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_no": user.phone_no,
            "is_staff": user.is_staff,
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "email": {"required": True},
            "password": {"write_only": True},
        }


class UserStaffStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["is_staff"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "phone_no"]

    def validate_first_name(self, value):
        if value == "":
            raise serializers.ValidationError("First name cannot be empty.")
        return value

    def validate_last_name(self, value):
        if value == "":
            raise serializers.ValidationError("Last name cannot be empty.")
        return value

    def validate_phone_no(self, value):
        if value == "":
            raise serializers.ValidationError("Phone number cannot be empty.")
        return value

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_no",
            "stripe_customer_id",
            "is_staff",
        ]
