import pytest
from django.urls import reverse
from rest_framework import status

from expenses.models import Group

pytestmark = pytest.mark.django_db


def test_register_creates_a_user(client):
    response = client.post(
        reverse("api:register"),
        {"username": "alice", "email": "alice@example.com", "password": "password123"},
        content_type="application/json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["username"] == "alice"


def test_login_returns_a_token(client, create_user):
    create_user("alice")
    response = client.post(
        reverse("api-login"),
        {"username": "alice", "password": "password123"},
        content_type="application/json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "token" in response.json()


def test_password_reset_request_sends_an_email_for_a_known_address(client, create_user, mailoutbox):
    create_user("alice", email="alice@example.com")

    response = client.post(
        reverse("api:password-reset-request"),
        {"email": "alice@example.com"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(mailoutbox) == 1
    assert "alice@example.com" in mailoutbox[0].to


def test_password_reset_request_is_silent_for_an_unknown_address(client, mailoutbox):
    response = client.post(
        reverse("api:password-reset-request"),
        {"email": "nobody@example.com"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert len(mailoutbox) == 0


def test_password_reset_confirm_changes_the_password(client, create_user):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    user = create_user("alice", email="alice@example.com")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    response = client.post(
        reverse("api:password-reset-confirm"),
        {"uid": uid, "token": token, "password": "newpassword123"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password("newpassword123")


def test_password_reset_confirm_rejects_an_invalid_token(client, create_user):
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    user = create_user("alice", email="alice@example.com")
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    response = client.post(
        reverse("api:password-reset-confirm"),
        {"uid": uid, "token": "not-a-real-token", "password": "newpassword123"},
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    user.refresh_from_db()
    assert not user.check_password("newpassword123")


def test_creating_a_group_adds_the_creator_as_a_member(api_client):
    client = api_client(username="alice")
    response = client.post(reverse("api:group-list"), {"name": "Trip to Rome"})

    assert response.status_code == status.HTTP_201_CREATED
    group = Group.objects.get(pk=response.json()["id"])
    assert list(group.members.values_list("username", flat=True)) == ["alice"]


def test_group_list_only_shows_the_users_own_groups(api_client):
    alice_client = api_client(username="alice")
    api_client(username="bob").post(reverse("api:group-list"), {"name": "Bob's group"})
    alice_client.post(reverse("api:group-list"), {"name": "Alice's group"})

    response = alice_client.get(reverse("api:group-list"))

    assert [g["name"] for g in response.json()] == ["Alice's group"]


def test_non_member_cannot_view_a_group(api_client):
    alice_client = api_client(username="alice")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]

    bob_client = api_client(username="bob")
    response = bob_client.get(reverse("api:group-detail", args=[group_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_only_creator_can_delete_a_group(api_client):
    alice_client = api_client(username="alice")
    bob_client = api_client(username="bob")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]
    alice_client.post(reverse("api:group-members", args=[group_id]), {"username": "bob"})

    response = bob_client.delete(reverse("api:group-detail", args=[group_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Group.objects.filter(pk=group_id).exists()


def test_expense_with_equal_split_creates_matching_shares(api_client):
    alice_client = api_client(username="alice")
    api_client(username="bob")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]
    alice_client.post(reverse("api:group-members", args=[group_id]), {"username": "bob"})

    response = alice_client.post(
        reverse("api:expense-list", args=[group_id]),
        {"description": "Dinner", "amount": "100.00", "split_equally_among": ["alice", "bob"]},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    shares = {share["user"]: share["amount"] for share in response.json()["shares"]}
    assert shares == {"alice": "50.00", "bob": "50.00"}


def test_a_group_member_can_delete_an_expense(api_client):
    from expenses.models import Expense

    alice_client = api_client(username="alice")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]
    expense_id = alice_client.post(
        reverse("api:expense-list", args=[group_id]),
        {"description": "Dinner", "amount": "100.00", "split_equally_among": ["alice"]},
        format="json",
    ).json()["id"]

    response = alice_client.delete(reverse("api:expense-detail", args=[group_id, expense_id]))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Expense.objects.filter(pk=expense_id).exists()


def test_a_non_member_cannot_delete_an_expense(api_client):
    from expenses.models import Expense

    alice_client = api_client(username="alice")
    bob_client = api_client(username="bob")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]
    expense_id = alice_client.post(
        reverse("api:expense-list", args=[group_id]),
        {"description": "Dinner", "amount": "100.00", "split_equally_among": ["alice"]},
        format="json",
    ).json()["id"]

    response = bob_client.delete(reverse("api:expense-detail", args=[group_id, expense_id]))

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Expense.objects.filter(pk=expense_id).exists()


def test_expense_with_custom_shares_must_add_up_to_the_total(api_client):
    alice_client = api_client(username="alice")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]

    response = alice_client.post(
        reverse("api:expense-list", args=[group_id]),
        {
            "description": "Dinner",
            "amount": "100.00",
            "shares": [{"user": "alice", "amount": "40.00"}],
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_expense_creation_rolls_back_if_a_share_fails(api_client, monkeypatch):
    from expenses.models import Expense, ExpenseShare

    alice_client = api_client(username="alice")
    api_client(username="bob")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]

    real_create = ExpenseShare.objects.create
    calls = []

    def flaky_create(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("share write blew up")
        return real_create(*args, **kwargs)

    monkeypatch.setattr(ExpenseShare.objects, "create", flaky_create)

    with pytest.raises(RuntimeError):
        alice_client.post(
            reverse("api:expense-list", args=[group_id]),
            {"description": "Dinner", "amount": "90.00", "split_equally_among": ["alice", "bob"]},
            format="json",
        )

    # The expense and its first share were rolled back with the failed one.
    assert not Expense.objects.filter(group_id=group_id).exists()
    assert not ExpenseShare.objects.exists()


def test_balances_endpoint_reflects_expenses_and_settlements(api_client):
    alice_client = api_client(username="alice")
    bob_client = api_client(username="bob")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]
    alice_client.post(reverse("api:group-members", args=[group_id]), {"username": "bob"})
    alice_client.post(
        reverse("api:expense-list", args=[group_id]),
        {"description": "Dinner", "amount": "100.00", "split_equally_among": ["alice", "bob"]},
        format="json",
    )

    balances = alice_client.get(reverse("api:group-balances", args=[group_id])).json()
    amounts = {entry["user"]["username"]: entry["amount"] for entry in balances["balances"]}
    assert amounts == {"alice": "50.00", "bob": "-50.00"}

    bob_client.post(reverse("api:settlement-list", args=[group_id]), {"paid_to": "alice", "amount": "50.00"})

    balances_after = alice_client.get(reverse("api:group-balances", args=[group_id])).json()
    assert balances_after["balances"] == []
    assert balances_after["suggested_settlements"] == []


def test_cannot_settle_up_with_yourself(api_client):
    alice_client = api_client(username="alice")
    group_id = alice_client.post(reverse("api:group-list"), {"name": "Trip"}).json()["id"]

    response = alice_client.post(
        reverse("api:settlement-list", args=[group_id]), {"paid_to": "alice", "amount": "10.00"}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
