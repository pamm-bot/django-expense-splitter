from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Expense, ExpenseShare, Group, Settlement


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            password=validated_data["password"],
        )


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)


class GroupSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Group
        fields = ["id", "name", "members", "created_by", "created_at"]
        read_only_fields = ["created_by"]


class AddMemberSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with that username.")


class ExpenseShareSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field="username", queryset=User.objects.all())

    class Meta:
        model = ExpenseShare
        fields = ["user", "amount"]


class ExpenseSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    shares = ExpenseShareSerializer(many=True, required=False)
    # Convenience input for the common case: split the amount evenly across
    # these usernames instead of specifying each share by hand.
    split_equally_among = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Expense
        fields = ["id", "description", "amount", "paid_by", "shares", "split_equally_among", "created_at"]

    def validate(self, data):
        if not data.get("shares") and not data.get("split_equally_among"):
            raise serializers.ValidationError("Provide either shares or split_equally_among.")
        return data

    def create(self, validated_data):
        group = self.context["group"]
        split_equally_among = validated_data.pop("split_equally_among", None)
        shares_data = validated_data.pop("shares", [])

        expense = Expense.objects.create(group=group, paid_by=self.context["request"].user, **validated_data)

        if split_equally_among:
            usernames = split_equally_among
            users = list(User.objects.filter(username__in=usernames))
            if len(users) != len(usernames):
                expense.delete()
                raise serializers.ValidationError(
                    "One or more usernames in split_equally_among were not found."
                )
            share_amount = (expense.amount / len(users)).quantize(Decimal("0.01"))
            remainder = expense.amount - (share_amount * len(users))
            for index, user in enumerate(users):
                amount = share_amount + (remainder if index == 0 else Decimal("0"))
                ExpenseShare.objects.create(expense=expense, user=user, amount=amount)
        else:
            total = sum((share["amount"] for share in shares_data), Decimal("0"))
            if total != expense.amount:
                expense.delete()
                raise serializers.ValidationError("Shares must add up to the expense amount.")
            for share in shares_data:
                ExpenseShare.objects.create(expense=expense, **share)

        return expense


class SettlementSerializer(serializers.ModelSerializer):
    paid_by = UserSerializer(read_only=True)
    paid_to = serializers.SlugRelatedField(slug_field="username", queryset=User.objects.all())

    class Meta:
        model = Settlement
        fields = ["id", "paid_by", "paid_to", "amount", "created_at"]

    def create(self, validated_data):
        group = self.context["group"]
        request_user = self.context["request"].user
        if validated_data["paid_to"] == request_user:
            raise serializers.ValidationError("You can't settle up with yourself.")
        return Settlement.objects.create(group=group, paid_by=request_user, **validated_data)
