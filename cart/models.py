from django.db import models

from accounts.models import CustomUser
from products.models import Product


class ShoppingSession(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    total = models.IntegerField(blank=True, default=0)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class CartItem(models.Model):
    session = models.ForeignKey(
        ShoppingSession, on_delete=models.CASCADE, related_name="cart_items"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_items"
    )
    quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)
