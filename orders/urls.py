from django.urls import path

from .views import (CreateOrder, CreateReviewView,
                    EligibleOrderItemsForReviewView, GetAllOrders,
                    PaymentListView, ProductReviewsView,
                    StripeWebhookCreateAPIView, UpdateOrderStatus)

urlpatterns = [
    path("order/session-checkout/", CreateOrder.as_view(), name="checkout-db-users"),
    path(
        "order/update/<int:pk>/",
        UpdateOrderStatus.as_view(),
        name="update-order-status",
    ),
    path("order/", GetAllOrders.as_view(), name="get-orders"),
    path(
        "stripe/webhook/", StripeWebhookCreateAPIView.as_view(), name="stripe-webhook"
    ),
    path("payments/", PaymentListView.as_view(), name="payment-list"),
    path("reviews/", CreateReviewView.as_view(), name="review-create"),
    path(
        "products/<int:product_id>/reviews/",
        ProductReviewsView.as_view(),
        name="product-reviews",
    ),
    path(
        "eligible-order-items-for-review/",
        EligibleOrderItemsForReviewView.as_view(),
        name="eligible-review",
    ),
]
