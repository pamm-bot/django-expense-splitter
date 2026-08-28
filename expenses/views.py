from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Group
from .permissions import IsGroupMember
from .serializers import (
    AddMemberSerializer,
    ExpenseSerializer,
    GroupSerializer,
    RegisterSerializer,
    SettlementSerializer,
    UserSerializer,
)
from .services import compute_balances, simplify_debts


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class GroupNestedMixin:
    """Shared by every view nested under /groups/<group_pk>/..."""

    def get_group(self):
        if not hasattr(self, "_group"):
            self._group = get_object_or_404(Group, pk=self.kwargs["group_pk"])
        return self._group


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return self.request.user.expense_groups.all()

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user)
        group.members.add(self.request.user)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get_group(self):
        return self.get_object()

    def perform_destroy(self, instance):
        if instance.created_by_id != self.request.user.id:
            raise PermissionDenied("Only the group's creator can delete it.")
        instance.delete()


class GroupMembersView(GroupNestedMixin, generics.CreateAPIView):
    serializer_class = AddMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["username"]
        group = self.get_group()
        group.members.add(user)
        return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class ExpenseListCreateView(GroupNestedMixin, generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get_queryset(self):
        return self.get_group().expenses.select_related("paid_by").prefetch_related("shares__user")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group"] = self.get_group()
        return context


class ExpenseDetailView(GroupNestedMixin, generics.RetrieveDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get_queryset(self):
        return self.get_group().expenses.all()


class SettlementListCreateView(GroupNestedMixin, generics.ListCreateAPIView):
    serializer_class = SettlementSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get_queryset(self):
        return self.get_group().settlements.select_related("paid_by", "paid_to")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["group"] = self.get_group()
        return context


class BalancesView(GroupNestedMixin, APIView):
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]

    def get(self, request, group_pk):
        group = self.get_group()
        balances = compute_balances(group)

        # Decimals are stringified explicitly: DRF's renderer only coerces
        # them through a DecimalField, and would otherwise round-trip these
        # as floats, which is exactly what you don't want for money.
        return Response(
            {
                "balances": [
                    {"user": UserSerializer(user).data, "amount": str(amount)}
                    for user, amount in balances.items()
                ],
                "suggested_settlements": [
                    {
                        "from": UserSerializer(txn["from"]).data,
                        "to": UserSerializer(txn["to"]).data,
                        "amount": str(txn["amount"]),
                    }
                    for txn in simplify_debts(balances)
                ],
            }
        )
