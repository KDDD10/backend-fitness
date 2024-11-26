from rest_framework import serializers

from products.models import Product
from products.serializers import GetProductSerializer

from .models import CartItem, ShoppingSession


class ProductSerializer(serializers.Serializer):
    class Meta:
        model = Product
        fields = ["id", "product_name", "product_price"]


class AddToCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["product", "quantity"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CartItemSerializer(serializers.ModelSerializer):
    product = GetProductSerializer()

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "created_at", "updated_at"]


class CartSessionSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingSession
        fields = ["session_id", "created_at", "updated_at"]
