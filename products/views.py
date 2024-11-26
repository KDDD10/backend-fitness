from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from products.models import Product, ProductImage, ProductInventory
from products.serializers import (GetProductSerializer,
                                  InventorySerializerPost,
                                  ProductInventorySerializer,
                                  ProductSerializer)
from utils.common import IsAdminUser


class AddProduct(generics.CreateAPIView):
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsAdminUser]


class GetAllProducts(generics.ListAPIView):
    queryset = Product.objects.prefetch_related("product_categories", "images").all()
    serializer_class = GetProductSerializer


class GetProductById(generics.RetrieveAPIView, generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = GetProductSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [IsAuthenticated(), IsAdminUser()]


class UpdateProduct(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_serializer(self, *args, **kwargs):
        # Ensure that partial updates are allowed
        kwargs.setdefault("partial", True)
        return super().get_serializer(*args, **kwargs)


class ProductInventoryList(generics.ListAPIView):
    queryset = ProductInventory.objects.select_related("product").all()
    serializer_class = ProductInventorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]


class AddOrUpdateInventory(generics.GenericAPIView):
    serializer_class = InventorySerializerPost
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product"]
            quantity = serializer.validated_data["quantity"]

            # Attempt to get an existing inventory item or create a new one
            inventory_item, created = ProductInventory.objects.get_or_create(
                product_id=product_id.id,
                defaults={"quantity": quantity},  # Default quantity if new
            )

            if not created:
                # If the item existed, update the quantity
                inventory_item.quantity += quantity
                inventory_item.save()
                status_message = "Inventory updated"
                status_code = status.HTTP_200_OK
            else:
                # If a new item was created
                status_message = "Inventory created"
                status_code = status.HTTP_201_CREATED

            return Response(
                {
                    "status": status_message,
                    "inventory": InventorySerializerPost(inventory_item).data,
                },
                status=status_code,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductPrimaryImageUpdateView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "id"  # Assuming product_id is the primary key

    def patch(self, request, *args, **kwargs):
        # Get the product using the product_id from URL
        product = self.get_object()  # Get product based on the `id` in the URL

        # Get the image_id from the request data
        image_id = request.data.get("image_id")

        if not image_id:
            return Response(
                {"error": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the ProductImage by ID
            product_image = ProductImage.objects.get(id=image_id)
        except ProductImage.DoesNotExist:
            return Response(
                {"error": "ProductImage not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Check if the ProductImage belongs to the same Product
        if product_image.product != product:
            return Response(
                {"error": "The image does not belong to this product"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set the primary image for the product
        product.product_primary_image = product_image
        product.save()

        # Return the updated product data
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
