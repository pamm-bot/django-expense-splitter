"""Populate the database with a realistic demo group.

Gives the live demo something to show on the group page (members,
expenses, non-trivial balances and a suggested-settlement list) and a
shared login recruiters can use without registering. Safe to re-run: it
wipes the demo group and its users first, then rebuilds them.

    python manage.py seed_demo
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from expenses.models import Expense, ExpenseShare, Group, Settlement

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo12345"
MEMBERS = ["demo", "sam", "alex", "jordan"]
GROUP_NAME = "Weekend in Lisbon"


def equal_shares(expense, users):
    """Split expense.amount evenly, dropping any rounding remainder on the
    first person — same rule the API uses."""
    per_person = (expense.amount / len(users)).quantize(Decimal("0.01"))
    remainder = expense.amount - per_person * len(users)
    for index, user in enumerate(users):
        amount = per_person + (remainder if index == 0 else Decimal("0"))
        ExpenseShare.objects.create(expense=expense, user=user, amount=amount)


class Command(BaseCommand):
    help = "Create (or reset) the 'Weekend in Lisbon' demo group."

    @transaction.atomic
    def handle(self, *args, **options):
        Group.objects.filter(name=GROUP_NAME).delete()
        User.objects.filter(username__in=MEMBERS).delete()

        users = {}
        for name in MEMBERS:
            user = User.objects.create_user(
                username=name,
                email=f"{name}@example.com",
                password=DEMO_PASSWORD,
            )
            users[name] = user

        demo, sam, alex, jordan = (users[n] for n in MEMBERS)

        group = Group.objects.create(name=GROUP_NAME, created_by=demo)
        group.members.add(demo, sam, alex, jordan)

        # Paid by, amount, and how to split it.
        airbnb = Expense.objects.create(
            group=group, description="Airbnb (3 nights)", amount=Decimal("480.00"), paid_by=demo
        )
        equal_shares(airbnb, [demo, sam, alex, jordan])

        ferry = Expense.objects.create(
            group=group, description="Ferry day trip to Cascais", amount=Decimal("140.00"), paid_by=sam
        )
        equal_shares(ferry, [demo, sam, alex, jordan])

        groceries = Expense.objects.create(
            group=group, description="Groceries", amount=Decimal("86.40"), paid_by=sam
        )
        equal_shares(groceries, [demo, sam, alex, jordan])

        dinner = Expense.objects.create(
            group=group,
            description="Dinner at Time Out Market",
            amount=Decimal("132.00"),
            paid_by=alex,
        )
        for user, amount in [
            (demo, "40.00"),
            (sam, "30.00"),
            (alex, "32.00"),
            (jordan, "30.00"),
        ]:
            ExpenseShare.objects.create(expense=dinner, user=user, amount=Decimal(amount))

        transit = Expense.objects.create(
            group=group, description="Tram + metro passes", amount=Decimal("24.00"), paid_by=jordan
        )
        equal_shares(transit, [demo, sam, alex, jordan])

        Settlement.objects.create(group=group, paid_by=jordan, paid_to=demo, amount=Decimal("50.00"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded '{GROUP_NAME}' with {len(MEMBERS)} members, "
                f"{group.expenses.count()} expenses and 1 settlement.\n"
                f"Demo login:  {DEMO_USERNAME} / {DEMO_PASSWORD}"
            )
        )
