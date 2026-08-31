import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """DRF throttling counts requests in the cache, which LocMemCache keeps
    across tests. Reset it each test so rate limits don't bleed between them."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def create_user(db):
    def _create_user(username, **kwargs):
        kwargs.setdefault("password", "password123")
        return User.objects.create_user(username=username, **kwargs)

    return _create_user


@pytest.fixture
def api_client(create_user):
    def _client_for(user=None, username="alice"):
        user = user or create_user(username)
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        client.user = user
        return client

    return _client_for
