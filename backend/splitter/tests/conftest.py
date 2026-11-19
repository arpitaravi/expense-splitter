import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture
def make_user(db):
    def _make(name):
        return get_user_model().objects.create_user(name, f"{name}@example.com", "pass12345")
    return _make


@pytest.fixture
def client_for():
    def _c(user):
        c = APIClient()
        c.force_authenticate(user)
        return c
    return _c
