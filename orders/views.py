import environ
import stripe
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser
from cart.models import CartItem, ShoppingSession
from plans.models import UserSubscription

from .models import (OrderDetails, OrderItems, Payments, Review,
                     SubscriptionPlan)
from .serializers import (GetReviewSerializer, OrderDetailsSerializer,
                          OrderItemSerializer, OrderStatusUpdateSerializer,
                          PaymentSerializer, ReviewSerializer)

env = environ.Env()
environ.Env.read_env()

stripe.api_key = env("STRIPE_SECRET_KEY")


class CreateOrder(CreateAPIView):
    serializer_class = OrderDetailsSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user

        session = get_object_or_404(ShoppingSession, user=user)

        cart_items = CartItem.objects.filter(session=session)
        if not cart_items.exists():
            return Response(
                {"detail": "No items in the cart."}, status=status.HTTP_404_NOT_FOUND
            )
        total_price = 0
        total_price = 0
        line_items = []
        for item in cart_items:
            total_price += item.product.product_price * item.quantity
            line_items.append(
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": item.product.product_name,
                        },
                        "unit_amount": int(item.product.product_price * 100),
                    },
                    "quantity": item.quantity,
                }
            )
        customer_id = user.stripe_customer_id
        if not customer_id:
            new_customer = stripe.Customer.create(
                email=user.email,
            )
            customer_id = new_customer.id
            user.stripe_customer_id = customer_id
            user.save()

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer=customer_id,
                line_items=line_items,
                mode="payment",
                payment_intent_data={"metadata": {"type": "order", "user_id": user.id}},
                # success_url='http://localhost:8000/payment/success?session_id={CHECKOUT_SESSION_ID}',
                # cancel_url='http://localhost:8000/payment/cancel',
                success_url=env("SUCCESS_URL"),
                cancel_url=env("CANCEL_URL"),
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(
            {"checkout_url": checkout_session.url}, status=status.HTTP_303_SEE_OTHER
        )


class UpdateOrderStatus(UpdateAPIView):
    queryset = OrderDetails.objects.all()
    serializer_class = OrderStatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data.get("order_status")

        if not request.user.is_staff:
            if new_status != OrderDetails.OrderStatus.CANCELED:
                raise PermissionDenied(
                    "Regular users can only update the status to 'canceled'."
                )

        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)


class GetAllOrders(ListAPIView):
    queryset = OrderDetails.objects.all()
    serializer_class = OrderDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        order_id = self.request.query_params.get("id", None)
        if order_id:
            # If 'id' is provided, return the specific order with that id
            try:
                order = OrderDetails.objects.get(id=order_id)
                return OrderDetails.objects.filter(
                    id=order.id
                )  # Return only the specific order
            except OrderDetails.DoesNotExist:
                raise NotFound("Order not found.")

        if user.is_staff:
            return OrderDetails.objects.all()
        else:
            return OrderDetails.objects.filter(user=user)


class StripeWebhookCreateAPIView(CreateAPIView):

    def create(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = env("STRIPE_WEBHOOK_SECRET")
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            return Response(
                {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.SignatureVerificationError:
            return Response(
                {"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST
            )
        session = None
        if hasattr(event["data"]["object"], "lines"):
            session = event["data"]["object"]["lines"]["data"][0]["metadata"]
            userId = session["user_id"]
            user = int(userId)
        else:
            session = event["data"]["object"]["metadata"]
            if session == {}:
                return Response(
                    {"status": "unhandled event"}, status=status.HTTP_200_OK
                )
            else:
                userId = session["user_id"]
                user = int(userId)

        if (
            event["type"] == "invoice.payment_succeeded"
            and session["type"] == "plan_subscription"
        ):

            try:
                user_id = CustomUser.objects.get(id=user)
                selected_plan = SubscriptionPlan.objects.get(
                    id=int(
                        event["data"]["object"]["subscription_details"]["metadata"][
                            "selected_plan"
                        ]
                    )
                )
                user_subscription = UserSubscription.objects.get(user=user_id)
                user_subscription.payment_status = True
                user_subscription.status = "active"
                user_subscription.save()
                sub_payment_details = Payments.objects.create(user=user_id)
                sub_payment_details.stripe_payment_id = event["data"]["object"][
                    "payment_intent"
                ]
                sub_payment_details.amount = (
                    event["data"]["object"]["amount_paid"] / 100
                )
                sub_payment_details.user = user_id
                sub_payment_details.payment_status = "paid"
                sub_payment_details.selected_plan_id = selected_plan
                sub_payment_details.save()
                print(f"Updated subscription for user {user} to active.")
            except UserSubscription.DoesNotExist:
                print(f"Subscription not found for user ID {user}.")
                return Response(
                    {"detail": "Subscription not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        elif event["type"] == "payment_intent.succeeded" and session["type"] == "order":

            user = CustomUser.objects.get(id=user)

            shopping_session = ShoppingSession.objects.get(user=user)
            cart_items = CartItem.objects.filter(session=shopping_session)
            if cart_items.exists():
                with transaction.atomic():
                    order = OrderDetails.objects.create(user=user)

                    total_price = 0
                    for item in cart_items:
                        OrderItems.objects.create(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.product_price,
                        )
                        total_price += item.product.product_price * item.quantity

                    order.total_price = total_price
                    order.save()
                    payment_details = Payments.objects.create(user=user)
                    payment_details.stripe_payment_id = event["data"]["object"]["id"]
                    payment_details.amount = event["data"]["object"]["amount"] / 100
                    payment_details.user = user
                    payment_details.payment_status = "paid"
                    payment_details.order_id = order
                    payment_details.save()

                    cart_items.delete()
                    shopping_session.total = 0
                    shopping_session.save()

                return Response(
                    {"status": "success", "order_id": order.id},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"error": "No items in the cart to create an order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "unhandled event"}, status=status.HTTP_200_OK)


class PaymentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        is_admin = IsAdminUser

        payment_type = request.query_params.get("type", None)
        payment_id = request.query_params.get("id", None)

        payments = Payments.objects.all()

        if not is_admin:
            payments = payments.filter(user=user)
        if payment_id:
            payment = get_object_or_404(Payments, id=payment_id)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        if payment_type:
            if payment_type == "subscription":
                payments = payments.filter(selected_plan_id__isnull=False)
            elif payment_type == "order":
                payments = payments.filter(order_id__isnull=False)

        serializer = PaymentSerializer(payments, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateReviewView(CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


def get_eligible_order_items_for_review(user, product_id):
    # Get all the OrderItems where the user ordered the specified product
    order_items = OrderItems.objects.filter(
        order__user=user,  # Filter orders placed by the user
        product_id=product_id,  # Filter by specific product
    )

    # Filter out OrderItems that already have reviews
    order_items_without_reviews = order_items.filter(
        review__isnull=True  # Only get order items that don't have a review
    )

    return order_items_without_reviews


class ProductReviewsView(ListAPIView):
    serializer_class = GetReviewSerializer

    def get_queryset(self):
        # Retrieve the product_id from the URL
        product_id = self.kwargs["product_id"]
        # Filter reviews for the specified product
        return Review.objects.filter(order_item__product_id=product_id)


class EligibleOrderItemsForReviewView(ListAPIView):
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        product_id = self.request.query_params.get("product_id")

        if not product_id:
            return OrderItems.objects.none()

        return get_eligible_order_items_for_review(user, product_id)
