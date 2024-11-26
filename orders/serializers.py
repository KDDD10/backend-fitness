from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import OrderDetails, OrderItems, Payments, Review


class OrderItemsSerializer(serializers.ModelSerializer):
    # Product=ProductSerializer()
    class Meta:
        model = OrderItems
        fields = ["product", "quantity", "price"]


class OrderDetailsSerializer(serializers.ModelSerializer):
    items = OrderItemsSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = OrderDetails
        fields = ["id", "user", "order_date", "total_price", "order_status", "items"]


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDetails
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payments
        fields = "__all__"


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "order_item", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate(self, data):
        user = self.context["request"].user
        order_item = data.get("order_item")

        if Review.objects.filter(user=user, order_item=order_item).exists():
            raise serializers.ValidationError("You have already reviewed this item.")

        return data


class GetReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(
        source="order_item.product.name", read_only=True
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "product_name",
            "order_item",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "product_name"]


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItems
        fields = ["id", "order_id"]
