import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from expenses.models import Expense, ExpenseShare, Group, Settlement

pytestmark = pytest.mark.django_db


def test_group_str(create_user):
    alice = create_user("alice")
    group = Group.objects.create(name="Trip to Rome", created_by=alice)
    assert str(group) == "Trip to Rome"


def test_expense_share_is_unique_per_user_per_expense(create_user):
    alice = create_user("alice")
    bob = create_user("bob")
    group = Group.objects.create(name="Trip", created_by=alice)
    expense = Expense.objects.create(group=group, description="Dinner", amount="100.00", paid_by=alice)
    ExpenseShare.objects.create(expense=expense, user=bob, amount="50.00")

    with pytest.raises(IntegrityError):
        ExpenseShare.objects.create(expense=expense, user=bob, amount="10.00")


def test_settlement_cannot_be_with_self(create_user):
    alice = create_user("alice")
    group = Group.objects.create(name="Trip", created_by=alice)
    settlement = Settlement(group=group, paid_by=alice, paid_to=alice, amount="10.00")

    with pytest.raises(ValidationError):
        settlement.full_clean()
