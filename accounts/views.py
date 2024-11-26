import stripe
from django.contrib.auth import get_user_model
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import CustomUser
from utils.common import IsAdminUser

from .serializers import (CustomTokenCreateSerializer,
                          CustomUserCreateSerializer,
                          UserStaffStatusSerializer, UserUpdateSerializer)


class CustomUserRegisterView(APIView):
    def post(self, request):
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)  # Generate JWT token
            new_customer = stripe.Customer.create(
                email=user.email,
            )
            user.stripe_customer_id = new_customer.id
            user.save()
            return Response(
                {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone_no": user.phone_no,
                    "token": str(refresh.access_token),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomUserLoginView(APIView):

    def post(self, request):
        serializer = CustomTokenCreateSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


User = get_user_model()


class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_no": user.phone_no,
        }
        return Response(user_data, status=status.HTTP_200_OK)


class UserListView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserCreateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class UpdateStaffStatus(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserStaffStatusSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = "pk"


class UserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User updated successfully", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
