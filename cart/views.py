from django.db import models
from django.db.models import F, Sum
from rest_framework import status
from rest_framework.generics import (CreateAPIView, DestroyAPIView,
                                     ListAPIView, UpdateAPIView)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.models import Product, ProductInventory

from .models import CartItem, ShoppingSession
from .serializers import (AddToCartSerializer, CartItemSerializer,
                          CartSessionSerializer)


class AddToCartView(CreateAPIView):
    serializer_class = AddToCartSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product"]
            quantity = serializer.validated_data["quantity"]
            user = request.user

            # Ensure the user has a shopping session
            shopping_session, created = ShoppingSession.objects.get_or_create(user=user)

            # Ensure the product exists
            try:
                product = Product.objects.get(pk=product_id.id)

            except Product.DoesNotExist:
                return Response(
                    {"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND
                )

            # Get the ProductInventory instance and check stock
            try:
                product_inventory = ProductInventory.objects.get(product=product.id)
            except ProductInventory.DoesNotExist:
                return Response(
                    {"detail": "Product inventory not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if there is enough stock
            if product_inventory.quantity < quantity:
                return Response(
                    {"detail": "Insufficient stock."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the quantity in inventory
            product_inventory.quantity -= quantity
            product_inventory.save()

            # Calculate the total cost of the items being added
            quantity * product.product_price

            # Update or create the cart item
            cart_item, created = CartItem.objects.get_or_create(
                session=shopping_session,
                product=product,
                defaults={"quantity": quantity},
            )

            if not created:
                # If the cart item already exists, update the quantity
                cart_item.quantity += quantity
                cart_item.save()
                status_message = "Cart item updated"
                status_code = status.HTTP_200_OK
            else:
                status_message = "Cart item added"
                status_code = status.HTTP_201_CREATED

            # Update total in ShoppingSession
            total_quantity = CartItem.objects.filter(
                session=shopping_session
            ).aggregate(
                total_cost=models.Sum(
                    models.F("quantity") * models.F("product__product_price")
                )
            )
            total_cost_in_session = total_quantity["total_cost"] or 0
            shopping_session.total = total_cost_in_session
            shopping_session.save()

            return Response(
                {
                    "cart_item": AddToCartSerializer(cart_item).data,
                },
                status=status_code,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateCartItemView(UpdateAPIView):
    serializer_class = AddToCartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ensure we filter the cart items by the current user's shopping session
        user = self.request.user
        try:
            shopping_session = ShoppingSession.objects.get(user=user)
        except ShoppingSession.DoesNotExist:
            shopping_session = None

        # Return the cart items related to the user's shopping session
        return CartItem.objects.filter(session=shopping_session)

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product"]
            new_quantity = serializer.validated_data["quantity"]
            user = request.user

            # Ensure the user has a shopping session
            try:
                shopping_session = ShoppingSession.objects.get(user=user)
            except ShoppingSession.DoesNotExist:
                return Response(
                    {"detail": "Shopping session not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Ensure the product exists in the cart
            try:
                cart_item = CartItem.objects.get(
                    session=shopping_session, product=product_id
                )
            except CartItem.DoesNotExist:
                return Response(
                    {"detail": "Product not found in cart."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Ensure the product exists and check stock availability
            try:
                product_inventory = ProductInventory.objects.get(product=product_id)
            except ProductInventory.DoesNotExist:
                return Response(
                    {"detail": "Product inventory not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Calculate the difference in quantity (to update inventory)
            quantity_difference = new_quantity - cart_item.quantity

            # Check if the new quantity is within available stock
            if quantity_difference > 0:  # If increasing quantity
                if product_inventory.quantity < quantity_difference:
                    return Response(
                        {"detail": "Insufficient stock to fulfill the request."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # Update inventory: reduce stock for the new quantity
                product_inventory.quantity -= quantity_difference
            else:
                # Update inventory: restore stock for the reduced quantity
                product_inventory.quantity += abs(
                    quantity_difference
                )  # Correct logic for decreasing quantity

            product_inventory.save()

            # Update the cart item quantity
            cart_item.quantity = new_quantity
            cart_item.save()

            # Recalculate the total in the shopping session
            total_quantity = CartItem.objects.filter(
                session=shopping_session
            ).aggregate(total_cost=Sum(F("quantity") * F("product__product_price")))
            total_cost_in_session = total_quantity["total_cost"] or 0
            shopping_session.total = total_cost_in_session
            shopping_session.save()

            return Response(
                {
                    "cart_item": self.get_serializer(cart_item).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RemoveCartItem(DestroyAPIView):
    queryset = CartItem.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def delete(self, request, *args, **kwargs):
        cart_item = self.get_object()

        product = cart_item.product
        quantity = cart_item.quantity

        self.perform_destroy(cart_item)

        try:
            product_inventory = ProductInventory.objects.get(product=product.id)
            product_inventory.quantity += quantity
            product_inventory.save()
        except ProductInventory.DoesNotExist:
            return Response(
                {"detail": "Product inventory not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        shopping_session = cart_item.session
        total_quantity = CartItem.objects.filter(session=shopping_session).aggregate(
            total_cost=models.Sum(
                models.F("quantity") * models.F("product__product_price")
            )
        )

        total_cost_in_session = total_quantity["total_cost"] or 0
        shopping_session.total = total_cost_in_session
        shopping_session.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserCartItemsView(ListAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            cart_session = ShoppingSession.objects.get(user=user)
            return CartItem.objects.filter(session=cart_session)
        except ShoppingSession.DoesNotExist:
            return CartItem.objects.none()
