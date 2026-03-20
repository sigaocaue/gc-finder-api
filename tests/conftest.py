"""Fixtures compartilhadas entre todos os testes."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture()
def fake_user():
    """Usuário fake para bypass de autenticação."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.name = "Teste"
    user.email = "teste@email.com"
    user.role = "editor"
    user.is_active = True
    return user


@pytest.fixture()
def client(fake_user):
    """TestClient com dependência de autenticação sobrescrita."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
