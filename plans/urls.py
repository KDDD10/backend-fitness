from django.urls import path

from .views import (GoalCreateView, GoalDeleteView, GoalsByPlanView,
                    GoalUpdateView, MarkGoalCompleteView, PlanListCreateView,
                    PlanRetrieveUpdateDestroyView, PostListView,
                    PostPlanSuccessView, StartPlanView,
                    StripeSubscriptionWebhookView,
                    SubscriptionPlanListCreateView,
                    SubscriptionPlanRetrieveUpdateDestroyView,
                    UserAndAdminSubscriptionPlanView, UserPlanStatusView,
                    UserSubscriptionCreateView, UserUnsubscribeView)

urlpatterns = [
    path("plans/", PlanListCreateView.as_view(), name="plan-list-create"),
    path(
        "plans/<int:pk>/", PlanRetrieveUpdateDestroyView.as_view(), name="plan-detail"
    ),
    path("goals/", GoalCreateView.as_view(), name="goal-create"),
    path("goals/<int:pk>/update/", GoalUpdateView.as_view(), name="goal-update"),
    path("goals/delete/", GoalDeleteView.as_view(), name="goal-bulk-delete"),
    path("goals/plan/<int:plan_id>/", GoalsByPlanView.as_view(), name="goals-by-plan"),
    path(
        "subscription-plans/",
        SubscriptionPlanListCreateView.as_view(),
        name="subscription-plan-list-create",
    ),
    path(
        "subscription-plans/<int:pk>/",
        SubscriptionPlanRetrieveUpdateDestroyView.as_view(),
        name="subscription-plan-detail",
    ),
    path(
        "subscriptions/",
        UserSubscriptionCreateView.as_view(),
        name="user-subscription-list-create",
    ),
    path(
        "subscriptions/unsubscribe/",
        UserUnsubscribeView.as_view(),
        name="user-unsubscribe",
    ),
    path(
        "subscriptions/all/",
        UserAndAdminSubscriptionPlanView.as_view(),
        name="user-admin-subscription-plans",
    ),
    path(
        "stripe-subscription-webhook/",
        StripeSubscriptionWebhookView.as_view(),
        name="stripe_subscription_webhook",
    ),
    path("start-plan/", StartPlanView.as_view(), name="start-plan"),
    path(
        "user/goal/<int:goal_id>/complete/",
        MarkGoalCompleteView.as_view(),
        name="mark-goal-complete",
    ),
    path("user/plans/", UserPlanStatusView.as_view(), name="user-plan-status"),
    path("post-success/", PostPlanSuccessView.as_view(), name="post-plan-success"),
    path("posts/", PostListView.as_view(), name="post-list"),
]
