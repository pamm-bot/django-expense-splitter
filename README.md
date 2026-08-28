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
- Token authentication (`rest_framework.authtoken`)
- Vanilla JS frontend (fetch against the JSON API, no build step)
- pytest for tests
- Deployed on Heroku

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
| `/api/groups/<id>/settlements/` | GET, POST | List / record settle-ups |
| `/api/groups/<id>/balances/` | GET | Net balances + suggested settlements |

All endpoints except register/login require a member of the group and an
`Authorization: Token <token>` header.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then edit SECRET_KEY, DATABASE_URL, etc.
python manage.py migrate
python manage.py runserver
```

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
