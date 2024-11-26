from django.db import models
from rest_framework import serializers

from category.models import Category
from products.models import Product, ProductImage, ProductInventory
from utils.upload_files import upload_file


class ProductsImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    product_categories = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, write_only=True
    )
    categories = CategorySerializer(
        source="product_categories", many=True, read_only=True
    )
    images = ProductsImageSerializer(many=True, read_only=True)

    uploaded_images = serializers.ListField(
        child=serializers.URLField(),  # Change to accept URL strings
        write_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "product_name",
            "categories",
            "product_categories",
            "product_description",
            "product_price",
            "images",
            "uploaded_images",
        ]

    def create(self, validated_data):
        product_categories = validated_data.pop("product_categories", [])
        uploaded_images = validated_data.pop("uploaded_images", [])

        product = Product.objects.create(**validated_data)

        if product_categories:
            product.product_categories.set(product_categories)

        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def update(self, instance, validated_data):
        product_categories = validated_data.pop("product_categories", [])
        uploaded_images = validated_data.pop("uploaded_images", [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if product_categories:
            instance.product_categories.set(product_categories)

        if uploaded_images:
            for image in uploaded_images:
                ProductImage.objects.create(product=instance, image=image)

        return instance


class ImageGetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "created_at"]


class GetProductSerializer(serializers.ModelSerializer):
    total_quantity = serializers.SerializerMethodField()
    product_categories = CategorySerializer(many=True)
    images = ImageGetSerializer(many=True)
    product_primary_image = ImageGetSerializer()

    class Meta:
        model = Product
        fields = [
            "id",
            "product_name",
            "product_price",
            "product_description",
            "product_categories",
            "product_primary_image",
            "images",
            "total_quantity",
        ]

    def get_total_quantity(self, obj):
        total_quantity = ProductInventory.objects.filter(product=obj).aggregate(
            total=models.Sum("quantity")
        )["total"]
        return total_quantity or 0


class ProductInventorySerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = ProductInventory
        fields = "__all__"


class InventorySerializerPost(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = ProductInventory
        fields = "__all__"
