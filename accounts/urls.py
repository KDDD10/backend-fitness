from django.urls import path

from .views import (CustomUserLoginView, CustomUserRegisterView,
                    UpdateStaffStatus, UserInfoView, UserListView,
                    UserUpdateView)

urlpatterns = [
    path("register/", CustomUserRegisterView.as_view(), name="register"),
    path("login/", CustomUserLoginView.as_view(), name="login"),
    path("user-info/", UserInfoView.as_view(), name="user-info"),
    path("users/", UserListView.as_view(), name="users"),
    path(
        "users/update/status/<int:pk>", UpdateStaffStatus.as_view(), name="update-user"
    ),
    path("user/update/", UserUpdateView.as_view(), name="user-update"),
]
