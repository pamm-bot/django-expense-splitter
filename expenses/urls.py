from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("groups/", views.GroupListCreateView.as_view(), name="group-list"),
    path("groups/<int:pk>/", views.GroupDetailView.as_view(), name="group-detail"),
    path("groups/<int:group_pk>/members/", views.GroupMembersView.as_view(), name="group-members"),
    path("groups/<int:group_pk>/expenses/", views.ExpenseListCreateView.as_view(), name="expense-list"),
    path(
        "groups/<int:group_pk>/expenses/<int:pk>/", views.ExpenseDetailView.as_view(), name="expense-detail"
    ),
    path(
        "groups/<int:group_pk>/settlements/", views.SettlementListCreateView.as_view(), name="settlement-list"
    ),
    path("groups/<int:group_pk>/balances/", views.BalancesView.as_view(), name="group-balances"),
]
