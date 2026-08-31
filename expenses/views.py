from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Group
from .permissions import IsGroupMember
from .serializers import (
    AddMemberSerializer,
    ExpenseSerializer,
    GroupSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SettlementSerializer,
    UserSerializer,
)
from .services import compute_balances, simplify_debts

# The plain-text `{"detail": "..."}` body the password-reset views return.
_detail_response = inline_serializer(name="DetailResponse", fields={"detail": serializers.CharField()})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"


class LoginView(ObtainAuthToken):
    """DRF's token login, with throttling so it can't be brute-forced.
    ObtainAuthToken clears throttle_classes, so the scoped throttle has to
    be put back explicitly here."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(request=PasswordResetRequestSerializer, responses=_detail_response)
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{request.scheme}://{request.get_host()}/reset-password/{uid}/{token}/"
            send_mail(
                subject="Reset your Split Expenses password",
                message=(
                    "Someone requested a password reset for this account.\n\n"
                    f"Reset it here: {reset_url}\n\n"
                    "If you didn't request this, you can safely ignore this email."
                ),
                from_email=None,
                recipient_list=[user.email],
                using="default",
            )

        # Same response either way, so a bad guess can't confirm an email exists.
        return Response({"detail": "If an account with that email exists, a reset link has been sent."})


@extend_schema(request=PasswordResetConfirmSerializer, responses=_detail_response)
class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = None
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            pass

        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response(
                {"detail": "This reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data["password"])
        user.save()
        return Response({"detail": "Password has been reset."})


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


@extend_schema(
    responses=inline_serializer(
        name="GroupBalances",
        fields={
            "balances": inline_serializer(
                name="MemberBalance",
                many=True,
                fields={"user": UserSerializer(), "amount": serializers.CharField()},
            ),
            "suggested_settlements": inline_serializer(
                name="SuggestedSettlement",
                many=True,
                fields={
                    "from": UserSerializer(),
                    "to": UserSerializer(),
                    "amount": serializers.CharField(),
                },
            ),
        },
    )
)
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
