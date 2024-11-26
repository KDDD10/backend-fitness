from django.urls import path

from .views import (  # CreateOrder,; GetAllOrders,; UpdateOrderStatus,
    AddToCartView, RemoveCartItem, UpdateCartItemView, UserCartItemsView)

urlpatterns = [
    path("cart/add-item/", AddToCartView.as_view(), name="add-cart-item"),
    path("cart/get-items/", UserCartItemsView.as_view(), name="get-cart-items"),
    path("cart/remove-item/<int:pk>/", RemoveCartItem.as_view(), name="remove-item"),
    path(
        "cart/update-item/<int:pk>/",
        UpdateCartItemView.as_view(),
        name="update-item-custom-quantity",
    ),
]
