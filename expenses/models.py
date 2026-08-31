from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_groups"
    )
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="expense_groups")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses_paid"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description} ({self.amount})"

    def shares_total(self):
        return self.shares.aggregate(total=models.Sum("amount"))["total"] or Decimal("0")


class ExpenseShare(models.Model):
    """One participant's portion of an expense (equal or custom split)."""

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expense_shares"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="unique_share_per_user_per_expense"),
        ]

    def __str__(self):
        return f"{self.user} owes {self.amount} for {self.expense}"


class Settlement(models.Model):
    """A direct payment between two group members that settles part of a debt."""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements")
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settlements_paid"
    )
    paid_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="settlements_received"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def clean(self):
        if self.paid_by_id and self.paid_by_id == self.paid_to_id:
            raise ValidationError("A settlement must be between two different people.")

    def __str__(self):
        return f"{self.paid_by} paid {self.paid_to} {self.amount}"
