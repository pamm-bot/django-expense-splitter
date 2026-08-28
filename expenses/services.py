"""Balance calculation and debt simplification for a group.

Kept separate from views/serializers because it's the one piece of real
business logic in the app: turning a pile of expenses and settlements into
"who owes whom, and how do we clear it in the fewest payments".
"""

from collections import defaultdict
from decimal import Decimal


def compute_balances(group):
    """Net balance per member: positive means the group owes them money,
    negative means they owe the group money."""
    balances = defaultdict(Decimal)

    for expense in group.expenses.select_related("paid_by").prefetch_related("shares__user"):
        balances[expense.paid_by_id] += expense.amount
        for share in expense.shares.all():
            balances[share.user_id] -= share.amount

    for settlement in group.settlements.all():
        balances[settlement.paid_by_id] += settlement.amount
        balances[settlement.paid_to_id] -= settlement.amount

    members_by_id = {member.id: member for member in group.members.all()}
    return {
        members_by_id[user_id]: amount
        for user_id, amount in balances.items()
        if user_id in members_by_id and amount != 0
    }


def simplify_debts(balances):
    """Greedy debt simplification: repeatedly settle the biggest creditor
    against the biggest debtor. Minimizes the number of payments needed to
    bring every balance to zero, compared to settling every pair directly."""
    creditors = sorted(
        ((user, amount) for user, amount in balances.items() if amount > 0),
        key=lambda pair: pair[1],
        reverse=True,
    )
    debtors = sorted(
        ((user, -amount) for user, amount in balances.items() if amount < 0),
        key=lambda pair: pair[1],
        reverse=True,
    )

    transactions = []
    creditors = [list(pair) for pair in creditors]
    debtors = [list(pair) for pair in debtors]
    i = j = 0

    while i < len(creditors) and j < len(debtors):
        creditor, credit = creditors[i]
        debtor, debt = debtors[j]
        payment = min(credit, debt)

        transactions.append({"from": debtor, "to": creditor, "amount": payment})

        creditors[i][1] -= payment
        debtors[j][1] -= payment

        if creditors[i][1] == 0:
            i += 1
        if debtors[j][1] == 0:
            j += 1

    return transactions
