from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("groups/", views.GroupsView.as_view(), name="groups"),
    path("groups/<int:group_id>/", views.GroupDetailView.as_view(), name="group-detail"),
]
