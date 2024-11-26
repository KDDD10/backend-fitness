from django.urls import path

from products.views import (AddOrUpdateInventory, AddProduct, GetAllProducts,
                            GetProductById, ProductInventoryList,
                            ProductPrimaryImageUpdateView, UpdateProduct)

urlpatterns = [
    path("products/create/", AddProduct.as_view(), name="create-product"),
    path("products/", GetAllProducts.as_view(), name="get-products"),
    path("products/<int:pk>/", GetProductById.as_view(), name="single-product"),
    path("products/update/<int:pk>/", UpdateProduct.as_view(), name="update-product"),
    path(
        "products/inventory/", ProductInventoryList.as_view(), name="product-inventory"
    ),
    path(
        "products/inventory/update/",
        AddOrUpdateInventory.as_view(),
        name="product-inventory-update",
    ),
    path(
        "products/<int:id>/set-primary-image/",
        ProductPrimaryImageUpdateView.as_view(),
        name="set-primary-image",
    ),
]
