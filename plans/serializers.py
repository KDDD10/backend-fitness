from datetime import date, timedelta

from rest_framework import serializers

from accounts.models import CustomUser

from .models import (Goals, Plans, Post, SubscriptionPlan, UserGoalProgress,
                     UserPlan, UserSubscription)


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goals
        fields = ["id", "description", "day_number"]


class PlanSerializer(serializers.ModelSerializer):
    goals = GoalSerializer(many=True, read_only=True)  # Nested serializer for goals

    class Meta:
        model = Plans
        fields = [
            "id",
            "name",
            "plan_type",
            "description",
            "duration_days",
            "subscription_required",
            "goals",
        ]


class PlanCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plans
        fields = [
            "id",
            "name",
            "plan_type",
            "description",
            "duration_days",
            "subscription_required",
        ]


class GoalListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        unique_goals = {}
        for item in validated_data:
            plan = item.get("plan")
            day_number = item.get("day_number")

            # Check for uniqueness
            if (plan, day_number) not in unique_goals:
                unique_goals[(plan, day_number)] = item
            else:
                raise serializers.ValidationError(
                    f"Goal with plan ID {plan} and day number {day_number} already exists."
                )

        goals = [Goals(**item) for item in unique_goals.values()]
        return Goals.objects.bulk_create(goals)


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goals
        fields = ["id", "plan", "description", "day_number"]
        list_serializer_class = GoalListSerializer


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "price",
            "days",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "user",
            "subscription_plan",
            "start_date",
            "end_date",
            "status",
        ]
        read_only_fields = ["id", "user"]

    def validate(self, attrs):
        if "subscription_plan" not in attrs:
            raise serializers.ValidationError(
                {"subscription_plan": "This field is required."}
            )
        return attrs


class UserSubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscription
        fields = [
            "id",
            "user",
            "subscription_plan",
            "start_date",
            "end_date",
            "status",
        ]


class UserPlanSerializer(serializers.ModelSerializer):
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=Plans.objects.all(), source="plan", write_only=True
    )

    class Meta:
        model = UserPlan
        fields = ["plan_id", "start_date"]

    def validate_start_date(self, value):
        if value < date.today():
            raise serializers.ValidationError("Start date cannot be in the past.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        plan = validated_data["plan"]

        # Check if a user already has an active or completed plan to avoid duplicates
        if UserPlan.objects.filter(user=user, plan=plan).exists():
            raise serializers.ValidationError("User already has this plan.")

        # Create UserPlan with start and calculated end date
        user_plan = UserPlan.objects.create(
            user=user,
            plan=plan,
            start_date=validated_data["start_date"],
            end_date=validated_data["start_date"] + timedelta(days=plan.duration_days),
        )
        # Populate goals for this user plan
        user_plan.populate_user_goals()
        return user_plan


class MarkGoalCompleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserGoalProgress
        fields = ["status", "completion_date"]

    def validate_status(self, value):
        # Ensure the status can only be marked as 'completed'
        if value != UserGoalProgress.COMPLETED:
            raise serializers.ValidationError("Only 'completed' status is allowed.")
        return value

    def update(self, instance, validated_data):
        instance.status = validated_data.get("status", instance.status)
        instance.completion_date = validated_data.get("completion_date", None)
        instance.save()
        return instance


class PlanSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Plans
        fields = [
            "id",
            "name",
        ]


class UserPlanStatusSerializer(serializers.ModelSerializer):
    plan = PlanSerializer1()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()

    class Meta:
        model = UserPlan
        fields = ["plan", "start_date", "end_date", "status"]


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = Post
        fields = ["id", "user", "plan", "content", "image", "created_at", "updated_at"]
        read_only_fields = ["id", "user"]


class GoalPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goals
        fields = ["id", "description", "day_number"]


class PlanPostSerializer(serializers.ModelSerializer):
    goals = GoalPostSerializer(many=True)

    class Meta:
        model = Plans
        fields = ["id", "name", "plan_type", "description", "goals"]


class UserPostSerializer:
    class Meta:
        model = CustomUser
        fields = ["id", "first_name", "last_name", "email"]


class GetPostSerializer(serializers.ModelSerializer):
    plan = PlanPostSerializer()
    user = UserPostSerializer()

    class Meta:
        model = Post
        fields = ["user", "plan", "content", "image", "created_at"]
