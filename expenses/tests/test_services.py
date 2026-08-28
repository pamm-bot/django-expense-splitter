from decimal import Decimal

import pytest

from expenses.models import Expense, ExpenseShare, Group, Settlement
from expenses.services import compute_balances, simplify_debts

pytestmark = pytest.mark.django_db


def make_group(creator, *members):
    group = Group.objects.create(name="Trip", created_by=creator)
    group.members.add(creator, *members)
    return group


def test_compute_balances_for_a_single_expense(create_user):
    alice, bob = create_user("alice"), create_user("bob")
    group = make_group(alice, bob)
    expense = Expense.objects.create(group=group, description="Dinner", amount="100.00", paid_by=alice)
    ExpenseShare.objects.create(expense=expense, user=alice, amount="50.00")
    ExpenseShare.objects.create(expense=expense, user=bob, amount="50.00")

    balances = compute_balances(group)

    assert balances[alice] == Decimal("50.00")
    assert balances[bob] == Decimal("-50.00")


def test_compute_balances_nets_out_settlements(create_user):
    alice, bob = create_user("alice"), create_user("bob")
    group = make_group(alice, bob)
    expense = Expense.objects.create(group=group, description="Dinner", amount="100.00", paid_by=alice)
    ExpenseShare.objects.create(expense=expense, user=alice, amount="50.00")
    ExpenseShare.objects.create(expense=expense, user=bob, amount="50.00")
    Settlement.objects.create(group=group, paid_by=bob, paid_to=alice, amount="50.00")

    balances = compute_balances(group)

    assert balances == {}


def test_compute_balances_ignores_zero_net_members(create_user):
    alice, bob = create_user("alice"), create_user("bob")
    group = make_group(alice, bob)
    expense = Expense.objects.create(group=group, description="Split evenly", amount="20.00", paid_by=alice)
    ExpenseShare.objects.create(expense=expense, user=alice, amount="10.00")
    ExpenseShare.objects.create(expense=expense, user=bob, amount="10.00")
    # A second expense that reverses it exactly.
    expense2 = Expense.objects.create(group=group, description="Reverse", amount="10.00", paid_by=bob)
    ExpenseShare.objects.create(expense=expense2, user=alice, amount="10.00")

    balances = compute_balances(group)

    assert balances == {}


def test_simplify_debts_produces_minimal_transactions_for_three_people():
    alice, bob, carol = "alice", "bob", "carol"
    balances = {
        alice: Decimal("30.00"),
        bob: Decimal("-10.00"),
        carol: Decimal("-20.00"),
    }

    transactions = simplify_debts(balances)

    # Carol (biggest debtor) pays alice (only creditor) first, then bob.
    assert transactions == [
        {"from": carol, "to": alice, "amount": Decimal("20.00")},
        {"from": bob, "to": alice, "amount": Decimal("10.00")},
    ]


def test_simplify_debts_settles_every_balance_to_zero():
    balances = {
        "a": Decimal("15.00"),
        "b": Decimal("5.00"),
        "c": Decimal("-12.00"),
        "d": Decimal("-8.00"),
    }

    transactions = simplify_debts(balances)

    net = dict.fromkeys(balances, Decimal("0"))
    for txn in transactions:
        net[txn["from"]] -= txn["amount"]
        net[txn["to"]] += txn["amount"]

    for person, starting_balance in balances.items():
        assert net[person] == starting_balance
