from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models

from accounts.models import CustomUser


class Plans(models.Model):
    NUTRITION = "nutrition"
    EXERCISE = "exercise"
    PLAN_TYPES = [
        (NUTRITION, "Nutrition"),
        (EXERCISE, "Exercise"),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPES)
    description = models.TextField()
    duration_days = models.PositiveIntegerField()  # Duration in days for the plan
    subscription_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"


class Goals(models.Model):
    plan = models.ForeignKey(Plans, related_name="goals", on_delete=models.CASCADE)
    description = models.TextField()
    day_number = models.PositiveIntegerField()  # Day within the plan
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "plan",
            "day_number",
        )  # Ensures unique day numbers within each plan
        ordering = ["day_number"]  # Orders goals by day number within a plan

    def __str__(self):
        return f"{self.plan.name} - Day {self.day_number}"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    days = models.PositiveIntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.price}/month"


class UserSubscription(models.Model):
    ACTIVE = "active"
    INACTIVE = "inactive"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True
    )
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)  # Set to manage subscription end
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=INACTIVE)
    payment_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.subscription_plan.name} Subscription"


class UserPlan(models.Model):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plans, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Calculate end_date based on start_date and plan duration if not provided
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)
        # Populate UserGoalProgress records if newly created UserPlan
        if not self.user_goals.exists():
            self.populate_user_goals()

    def populate_user_goals(self):
        goals = self.plan.goals.all()
        for goal in goals:
            scheduled_date = self.start_date + timedelta(days=goal.day_number - 1)
            # Check if goal progress for this user plan and goal already exists
            UserGoalProgress.objects.get_or_create(
                user_plan=self,
                goal=goal,
                defaults={
                    "scheduled_date": scheduled_date,
                    "status": UserGoalProgress.PENDING,
                },
            )

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} (Status: {self.status})"


class UserGoalProgress(models.Model):
    PENDING = "pending"
    COMPLETED = "completed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETED, "Completed"),
    ]

    user_plan = models.ForeignKey(
        UserPlan, related_name="user_goals", on_delete=models.CASCADE
    )
    goal = models.ForeignKey(Goals, on_delete=models.CASCADE)
    scheduled_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    completion_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_plan.user.username} - {self.goal.description} (Status: {self.status})"

    class Meta:
        unique_together = (
            "user_plan",
            "goal",
        )  # Ensures each goal appears only once per UserPlan
        ordering = ["scheduled_date"]


class Post(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.ForeignKey("Plans", on_delete=models.CASCADE)
    content = models.TextField()
    image = models.ImageField(
        upload_to="post_images/", blank=True, null=True
    )  # Optional: Image for the post
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.user.username} for {self.plan.name} on {self.created_at}"
