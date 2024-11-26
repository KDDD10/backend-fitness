from django.db import models

from accounts.models import CustomUser
from plans.models import SubscriptionPlan
from products.models import Product


class OrderDetails(models.Model):
    class OrderStatus(models.TextChoices):
        IN_PROGRESS = "in-progress", "In Progress"
        CANCELED = "canceled", "Canceled"
        BOOKED = "booked", "Booked"
        DELIVERED = "delivered", "Delivered"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    order_status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.BOOKED
    )
    # payment_id= models.ForeignKey('PaymentDetails', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class OrderItems(models.Model):
    order = models.ForeignKey(
        OrderDetails, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class Payments(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    payment_status = models.CharField(
        max_length=150, choices=PaymentStatus, default=PaymentStatus.UNPAID
    )
    order_id = models.ForeignKey(
        OrderDetails, blank=True, null=True, on_delete=models.CASCADE
    )
    selected_plan_id = models.ForeignKey(
        SubscriptionPlan, blank=True, null=True, on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_payment_id = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    order_item = models.ForeignKey(OrderItems, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "user",
            "order_item",
        )

    def __str__(self):
        return f"Review for {self.order_item.product.name} by {self.user.username}"
