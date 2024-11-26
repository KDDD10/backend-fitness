from datetime import timedelta

import environ
import stripe
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import CustomUser
from utils.common import IsAdminUser

from .models import (Goals, Plans, Post, SubscriptionPlan, UserGoalProgress,
                     UserPlan, UserSubscription)
from .serializers import (GetPostSerializer, GoalSerializer,
                          MarkGoalCompleteSerializer,
                          PlanCreateUpdateSerializer, PlanSerializer,
                          PostSerializer, SubscriptionPlanSerializer,
                          UserPlanSerializer, UserPlanStatusSerializer,
                          UserSubscriptionPlanSerializer,
                          UserSubscriptionSerializer)

env = environ.Env()
environ.Env.read_env()
stripe.api_key = env("STRIPE_SECRET_KEY")


class PlanListCreateView(generics.ListCreateAPIView):
    queryset = Plans.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PlanCreateUpdateSerializer
        return PlanSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [IsAuthenticated(), IsAdminUser()]


# View for retrieving, updating, and deleting a single plan
class PlanRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Plans.objects.all()

    # Use different serializers for read and write operations
    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH", "DELETE"]:
            return PlanCreateUpdateSerializer
        return PlanSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [IsAuthenticated(), IsAdminUser()]


class GoalCreateView(generics.GenericAPIView):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, *args, **kwargs):
        # Set many=True to handle bulk creation
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GoalUpdateView(generics.UpdateAPIView):
    queryset = Goals.objects.all()
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    http_method_names = ["patch"]


class GoalDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def delete(self, request, *args, **kwargs):
        goal_ids = request.data.get("ids", [])
        Goals.objects.filter(id__in=goal_ids).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoalsByPlanView(generics.ListAPIView):
    serializer_class = GoalSerializer
    # permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        # Get the plan_id from URL parameters
        plan_id = self.kwargs["plan_id"]
        return Goals.objects.filter(plan_id=plan_id)


class SubscriptionPlanListCreateView(generics.ListCreateAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [IsAuthenticated(), IsAdminUser()]


class SubscriptionPlanRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return []
        else:
            return [IsAuthenticated(), IsAdminUser()]


class UserSubscriptionCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSubscriptionSerializer

    def get_queryset(self):
        return UserSubscription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        subscription_plan = serializer.validated_data.get("subscription_plan")
        plan_price = subscription_plan.price
        selected_plan = subscription_plan.id

        active_subscription = self.get_queryset().filter(status="active").first()
        inactive_subscription = self.get_queryset().filter(status="inactive").first()

        if active_subscription:
            raise serializers.ValidationError(
                {
                    "detail": "You must unsubscribe from your current subscription before creating a new one."
                }
            )

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=subscription_plan.days)

        if inactive_subscription:
            # Update the inactive subscription
            inactive_subscription.subscription_plan = subscription_plan
            inactive_subscription.start_date = start_date
            inactive_subscription.end_date = end_date
            inactive_subscription.status = "inactive"
            inactive_subscription.payment_status = False
            inactive_subscription.save()
            self.instance = inactive_subscription
        else:
            # Create a new subscription
            self.instance = serializer.save(
                user=self.request.user,
                status="active",
                start_date=start_date,
                end_date=end_date,
                payment_status=False,
            )
        self.payment_url = self.create_stripe_payment_session(plan_price)

    def create(self, request, *args, **kwargs):
        # Call super to handle creation and set response data
        response = super().create(request, *args, **kwargs)
        # response.data = UserSubscriptionSerializer(self.instance).data
        response.data = {
            "data": UserSubscriptionSerializer(self.instance).data,
            "payment_url": self.payment_url,  # Add payment URL to response
        }
        return response

    def create_stripe_payment_session(self, amount):
        user = self.request.user
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
            )
            user.stripe_customer_id = customer.id
            user.save()
        else:
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
        session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": self.instance.subscription_plan.name,
                        },
                        "unit_amount": int(amount * 100),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }
            ],
            mode="subscription",
            subscription_data={
                "metadata": {
                    "type": "plan_subscription",
                    "user_id": user.id,
                    "selected_plan": self.instance.subscription_plan.id,
                }
            },
            metadata={"type": "plan_subscription", "user_id": user.id},
            success_url=env("SUBSCRIPTION_SUCCESS_URL"),
            cancel_url=env("SUBSCRIPTION_CANCEL_URL"),
        )
        return session.url


class UserUnsubscribeView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = UserSubscription.objects.all()

    def get_object(self):
        subscription = self.queryset.filter(
            user=self.request.user, status="active"
        ).first()
        if not subscription:
            raise Http404("No active subscription found.")
        return subscription

    def patch(self, request, *args, **kwargs):
        subscription = self.get_object()
        subscription.status = "inactive"
        subscription.save()
        return Response(
            {"detail": "Subscription successfully canceled."}, status=status.HTTP_200_OK
        )


class UserAndAdminSubscriptionPlanView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if IsAdminUser:
            plans = UserSubscription.objects.all()
            serializer = UserSubscriptionPlanSerializer(plans, many=True)
            return Response(serializer.data, status=200)
        else:
            user_subscriptions = UserSubscription.objects.filter(user=request.user)
            serializer = UserSubscriptionPlanSerializer(user_subscriptions, many=True)
            return Response(serializer.data, status=200)


class StripeSubscriptionWebhookView(generics.CreateAPIView):
    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META["HTTP_STRIPE_SIGNATURE"]
        webhook_secret = env("STRIPE_WEBHOOK_SECRET_SUBSCRIPTION")

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)

        except ValueError as e:
            print(f"Invalid payload: {e}")
            return Response(
                {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
            )

        except stripe.error.SignatureVerificationError as e:
            print(f"Invalid signature: {e}")
            return Response(
                {"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST
            )

        if event["type"] == "invoice.payment_succeeded":
            session = event["data"]["object"]
            print(event, 60609090)

            if session["metadata"].get("type") == "plan_subscription":
                user_id = session["metadata"].get("user_id")
                user = int(user_id)
                print(user)
                try:
                    user_subscription = UserSubscription.objects.get(id=user)
                    user_subscription.payment_status = True
                    user_subscription.status = "active"
                    user_subscription.save()
                    print(f"Updated subscription for user {user_id} to active.")
                except UserSubscription.DoesNotExist:
                    print(f"Subscription not found for user ID {user_id}.")
                    return Response(
                        {"detail": "Subscription not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )

        return Response(status=status.HTTP_200_OK)


class StartPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserPlanSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            user_plan = serializer.save()
            return Response(
                {"message": "Plan started successfully", "data": serializer.data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarkGoalCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, goal_id):
        # Retrieve the goal progress for the logged-in user
        try:
            goal_progress = UserGoalProgress.objects.get(
                id=goal_id, user_plan__user=request.user
            )
        except UserGoalProgress.DoesNotExist:
            return Response(
                {"detail": "Goal progress not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Serialize the data to update the goal's status
        serializer = MarkGoalCompleteSerializer(
            goal_progress, data=request.data, partial=True
        )

        if serializer.is_valid():
            # Save the updated goal progress
            updated_goal_progress = serializer.save()

            # Check if all goals for the user's plan are completed
            user_plan = updated_goal_progress.user_plan
            all_goals_completed = (
                user_plan.user_goals.filter(status=UserGoalProgress.PENDING).count()
                == 0
            )

            # If all goals are completed, mark the UserPlan as completed
            if all_goals_completed:
                user_plan.status = UserPlan.COMPLETED
                user_plan.save()

            return Response(
                {"message": "Goal marked as completed", "data": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPlanStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan_id = request.query_params.get("id", None)

        if plan_id:
            # Fetch the user plan with the specific plan_id
            try:
                user_plan = UserPlan.objects.get(user=request.user, plan_id=plan_id)
                # Serialize and return the data for the specific plan
                serializer = UserPlanStatusSerializer(user_plan)
                return Response(
                    {"message": "User plan found.", "data": serializer.data},
                    status=status.HTTP_200_OK,
                )
            except UserPlan.DoesNotExist:
                return Response(
                    {
                        "detail": "User does not have this plan or the plan does not exist."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Fetch all user plans for the logged-in user
            user_plans = UserPlan.objects.filter(user=request.user)

            # If no plans are found, return a message
            if not user_plans.exists():
                return Response(
                    {"detail": "No plans found for the user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Serialize and return data for all user plans
            serializer = UserPlanStatusSerializer(user_plans, many=True)
            return Response(
                {"message": "User plans found.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )


class PostPlanSuccessView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PostSerializer

    def perform_create(self, serializer):
        user = self.request.user
        plan = serializer.validated_data["plan"]

        # Check if the user has completed all goals for the given plan
        user_plan = UserPlan.objects.filter(
            user=user, plan=plan, status=UserPlan.COMPLETED
        ).first()
        if not user_plan:
            raise ValidationError("User has not completed the plan.")

        # Check if all goals are completed
        completed_goals = UserGoalProgress.objects.filter(
            user_plan=user_plan, status=UserGoalProgress.COMPLETED
        )
        total_goals = user_plan.plan.goals.count()

        if completed_goals.count() != total_goals:
            raise ValidationError("User has not completed all the goals for this plan.")

        # If the user has completed all goals, create the post
        serializer.save(user=user)

    def create(self, request, *args, **kwargs):
        # Handle the post creation logic
        return super().create(request, *args, **kwargs)


class PostListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GetPostSerializer

    def get_queryset(self):
        # If 'user' query parameter is provided, filter by user
        user_id = self.request.query_params.get("user", None)
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                return Post.objects.filter(user=user)
            except CustomUser.DoesNotExist:
                return (
                    Post.objects.none()
                )  # Return an empty queryset if the user doesn't exist
        else:
            # If no 'user' query param, return all posts
            return Post.objects.all()

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"detail": "No posts found."}, status=404)

        # Serialize and return the post data
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {"message": "Posts retrieved successfully.", "data": serializer.data},
            status=200,
        )
