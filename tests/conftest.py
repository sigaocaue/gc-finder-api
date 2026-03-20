"""Fixtures compartilhadas entre todos os testes."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from faker import Faker
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.user import User

fake = Faker()


@pytest.fixture()
def fake_user():
    """Usuário fake para bypass de autenticação."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.name = fake.name()
    user.email = fake.email()
    user.role = "editor"
    user.is_active = True
    return user


@pytest.fixture()
def mock_db():
    """Sessão de banco mockada para rotas que dependem de DbSession."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture()
def client(fake_user, mock_db):
    """TestClient com dependências de autenticação e banco sobrescritas."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
