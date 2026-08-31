# Split Expenses

[![CI](https://github.com/pamm-bot/django-expense-splitter/actions/workflows/ci.yml/badge.svg)](https://github.com/pamm-bot/django-expense-splitter/actions/workflows/ci.yml)

A Splitwise-style expense splitter: create a group, log shared expenses, and
see who owes whom — with a debt-simplification algorithm that works out the
fewest payments needed to settle everyone up.

Built as a REST API (Django REST Framework) with a small JS frontend
consuming it over HTTP, rather than a single server-rendered app — the two
sides only ever talk through the same JSON endpoints an external client
would use.

**Live demo:** https://split-expenses-pam-05e9be4c8938.herokuapp.com/

## Features

- **Accounts** — token-based authentication; register and log in via the API,
  with email-based password reset if you forget it
- **Groups** — create a group, add members by username
- **Expenses** — log what was paid and by whom, split equally across
  members or with custom per-person amounts
- **Balances** — net balance per member, computed from every expense and
  settlement in the group
- **Debt simplification** — a greedy algorithm reduces the group's debts to
  the minimum number of payments needed to clear them, instead of everyone
  settling with everyone
- **Settle up** — record a direct payment between two members

## Stack

- Django 6.1, Django REST Framework, PostgreSQL
- Token authentication (`rest_framework.authtoken`), with scoped rate
  limiting on the auth endpoints
- OpenAPI 3 schema + Swagger UI via `drf-spectacular`
- WhiteNoise for static files, `django-cors-headers` for cross-origin API access
- Vanilla JS frontend (fetch against the JSON API, no build step)
- pytest for tests
- Deployed on Heroku

## Design decisions

- **API-first, not server-rendered.** The frontend is just another client of
  the JSON API — it has no privileged access to the database. This keeps the
  contract honest and means the same endpoints would serve a mobile app or a
  third-party integration without change.
- **Balance logic lives in [`expenses/services.py`](expenses/services.py).**
  Turning a pile of expenses and settlements into "who owes whom, in the
  fewest payments" is the one piece of real domain logic here, so it sits in
  plain functions that are unit-tested on their own, away from views,
  serializers and the ORM.
- **Greedy debt simplification.** Repeatedly settle the largest creditor
  against the largest debtor. It doesn't always find the theoretical minimum
  (that problem is NP-hard), but it's simple, predictable, and in practice
  gives `n - 1` payments or fewer for a group of `n`.
- **Money is `Decimal` end to end**, and the balances endpoint serialises
  amounts as strings — DRF's JSON renderer would otherwise round-trip them
  through `float`, which is exactly what you don't want for currency.
- **Token auth over sessions/JWT.** The API is stateless and consumed by a
  script-like client; DRF's built-in `authtoken` is the least machinery that
  does the job. The auth endpoints are rate limited so the login and
  password-reset routes can't be hammered.
- **Vanilla JS frontend.** No build step, no framework — enough to exercise
  the API and keep the repo's focus on the backend. Each page's script lives
  in its own file under [`static/js/`](static/js/).

## API overview

| Endpoint | Method | Description |
|---|---|---|
| `/api/auth/register/` | POST | Create an account |
| `/api/auth/login/` | POST | Get an auth token |
| `/api/auth/password-reset/` | POST | Request a reset email |
| `/api/auth/password-reset/confirm/` | POST | Set a new password from the emailed link |
| `/api/groups/` | GET, POST | List / create your groups |
| `/api/groups/<id>/` | GET, PATCH, DELETE | Group detail (delete: creator only) |
| `/api/groups/<id>/members/` | POST | Add a member by username |
| `/api/groups/<id>/expenses/` | GET, POST | List / log expenses |
| `/api/groups/<id>/expenses/<id>/` | GET, DELETE | Expense detail / delete |
| `/api/groups/<id>/settlements/` | GET, POST | List / record settle-ups |
| `/api/groups/<id>/balances/` | GET | Net balances + suggested settlements |
| `/api/schema/` | GET | OpenAPI 3 schema (YAML) |
| `/api/docs/` | GET | Swagger UI, browse and try the API |

All endpoints except register/login require a member of the group and an
`Authorization: Token <token>` header. The auth endpoints are rate limited
(login and register 20/hour, password-reset requests 5/hour, per client IP).

## Example flow

```bash
BASE=http://localhost:8000

# Register two accounts
curl -s $BASE/api/auth/register/ -H 'Content-Type: application/json' \
  -d '{"username": "alice", "email": "alice@example.com", "password": "hunter2!!"}'
curl -s $BASE/api/auth/register/ -H 'Content-Type: application/json' \
  -d '{"username": "bob", "password": "hunter2!!"}'

# Log in as alice and grab her token
TOKEN=$(curl -s $BASE/api/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "hunter2!!"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
AUTH="Authorization: Token $TOKEN"

# Create a group and add bob
GID=$(curl -s $BASE/api/groups/ -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name": "Sicily trip"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
curl -s $BASE/api/groups/$GID/members/ -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"username": "bob"}'

# Alice pays 60.00, split equally between alice and bob
curl -s $BASE/api/groups/$GID/expenses/ -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"description": "Groceries", "amount": "60.00", "split_equally_among": ["alice", "bob"]}'

# See who owes whom, plus the suggested minimal settlements
curl -s $BASE/api/groups/$GID/balances/ -H "$AUTH"

# Bob settles his 30.00 with alice (settlements are recorded by the payer,
# so this call uses bob's token)
BOB_TOKEN=$(curl -s $BASE/api/auth/login/ -H 'Content-Type: application/json' \
  -d '{"username": "bob", "password": "hunter2!!"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["token"])')
curl -s $BASE/api/groups/$GID/settlements/ -H "Authorization: Token $BOB_TOKEN" -H 'Content-Type: application/json' \
  -d '{"paid_to": "alice", "amount": "30.00"}'
```

For a custom split, send `shares` instead of `split_equally_among` — a list of
`{"user": "<username>", "amount": "<value>"}` that must add up to the expense
amount.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then edit SECRET_KEY, DATABASE_URL, etc.
python manage.py migrate
python manage.py seed_demo   # optional: a populated "Weekend in Lisbon" group
python manage.py runserver
```

`seed_demo` creates the `demo` / `demo12345` login and a group with a
handful of expenses and a settlement, so the balances and suggested-payment
views have something to show. It's safe to re-run — it resets that data.

Password reset emails need a Gmail account with an
[App Password](https://myaccount.google.com/apppasswords) (`EMAIL_HOST_USER`
/ `EMAIL_HOST_PASSWORD` in `.env`) — optional locally, reset requests just
won't send without it.

The frontend is served from the same app at `/`.

## Tests

```bash
pytest
```

Runs automatically on every push and pull request via GitHub Actions.

## Code quality

```bash
black .      # formatting
flake8 .     # linting
python manage.py check --deploy   # production security settings
```
