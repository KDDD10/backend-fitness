from django.urls import path

from .views import CategoryDetails, CategoryList

urlpatterns = [
    path("category/", CategoryList.as_view(), name="category-list"),
    path("category/<int:pk>/", CategoryDetails.as_view(), name="category-details"),
]
