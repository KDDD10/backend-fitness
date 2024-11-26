from django.db import models

from category.models import Category


class Product(models.Model):

    product_name = models.CharField(
        max_length=200,
        blank=False,
    )
    product_categories = models.ManyToManyField(Category, related_name="products")
    product_description = models.TextField(blank=False)
    product_price = models.IntegerField(blank=False)
    product_primary_image = models.ForeignKey(
        "ProductImage",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="product_primary_image",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)


class ProductInventory(models.Model):
    product = models.OneToOneField(
        Product, related_name="inventory", on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)
