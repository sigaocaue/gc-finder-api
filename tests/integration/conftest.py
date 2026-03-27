"""Fixtures de integração — banco SQLite em memória com tabelas reais."""

import uuid as uuid_module
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.sqlite.base import DATETIME as SQLiteDATETIME
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models import Gc, GcLeader, GcMedia, GcMeeting, Leader, LeaderContact, RefreshToken, User
from app.utils.security import hash_password, create_access_token


# ------------------------------------------------------------------ #
# Adaptador de UUID do PostgreSQL para SQLite
# ------------------------------------------------------------------ #

_orig_bind = PG_UUID.bind_processor
_orig_result = PG_UUID.result_processor


def _sqlite_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, uuid_module.UUID):
                return str(value)
            return str(value)
        return process
    return _orig_bind(self, dialect)


def _sqlite_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        if self.as_uuid:
            def process(value):
                if value is None:
                    return None
                if isinstance(value, uuid_module.UUID):
                    return value
                return uuid_module.UUID(value)
            return process
        return None
    return _orig_result(self, dialect, coltype)


PG_UUID.bind_processor = _sqlite_bind_processor
PG_UUID.result_processor = _sqlite_result_processor


# Adaptador de DateTime(timezone=True) para SQLite (retorna datetime aware)
_orig_sqlite_dt_result = SQLiteDATETIME.result_processor


def _tz_aware_result_processor(self, dialect, coltype):
    orig_processor = _orig_sqlite_dt_result(self, dialect, coltype)
    if self.timezone:
        def process(value):
            if value is None:
                return None
            result = orig_processor(value) if orig_processor else value
            if isinstance(result, str):
                result = datetime.fromisoformat(result)
            if isinstance(result, datetime) and result.tzinfo is None:
                return result.replace(tzinfo=timezone.utc)
            return result
        return process
    return orig_processor


SQLiteDATETIME.result_processor = _tz_aware_result_processor


# ------------------------------------------------------------------ #
# Engine e sessão SQLite async
# ------------------------------------------------------------------ #

_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(_TEST_DATABASE_URL, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _setup_db():
    """Cria todas as tabelas antes de cada teste e dropa ao final."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session() as session:
        yield session


# ------------------------------------------------------------------ #
# Usuários de teste persistidos no banco
# ------------------------------------------------------------------ #

@pytest.fixture()
async def admin_user() -> User:
    """Cria um usuário admin real no banco de teste."""
    async with _async_session() as session:
        user = User(
            id=uuid_module.uuid4(),
            name="Admin Test",
            email="admin@test.com",
            password_hash=hash_password("admin123"),
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture()
async def editor_user() -> User:
    """Cria um usuário editor real no banco de teste."""
    async with _async_session() as session:
        user = User(
            id=uuid_module.uuid4(),
            name="Editor Test",
            email="editor@test.com",
            password_hash=hash_password("editor123"),
            role="editor",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ------------------------------------------------------------------ #
# Tokens JWT válidos
# ------------------------------------------------------------------ #

@pytest.fixture()
def admin_token(admin_user: User) -> str:
    return create_access_token({"sub": str(admin_user.id)})


@pytest.fixture()
def editor_token(editor_user: User) -> str:
    return create_access_token({"sub": str(editor_user.id)})


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------ #
# TestClient com banco real (sem mock de DB)
# ------------------------------------------------------------------ #

@pytest.fixture()
def client():
    """TestClient com banco SQLite real — sem override de autenticação."""
    from httpx import ASGITransport, AsyncClient

    app.dependency_overrides[get_db] = _get_test_db

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
    app.dependency_overrides.clear()


# ------------------------------------------------------------------ #
# Helpers para criar entidades auxiliares diretamente no banco
# ------------------------------------------------------------------ #

@pytest.fixture()
async def create_leader():
    """Factory fixture para criar um líder no banco."""
    async def _create(name: str = "Líder Teste", **kwargs) -> Leader:
        async with _async_session() as session:
            kwargs.setdefault("is_active", True)
            leader = Leader(
                id=uuid_module.uuid4(),
                name=name,
                **kwargs,
            )
            session.add(leader)
            await session.commit()
            await session.refresh(leader)
            return leader
    return _create


@pytest.fixture()
async def create_gc():
    """Factory fixture para criar um GC no banco (sem geocodificação)."""
    async def _create(name: str = "GC Teste", **kwargs) -> Gc:
        defaults = {
            "zip_code": "01001000",
            "street": "Praça da Sé",
            "neighborhood": "Sé",
            "city": "São Paulo",
            "state": "SP",
            "is_active": True,
        }
        defaults.update(kwargs)
        async with _async_session() as session:
            gc = Gc(id=uuid_module.uuid4(), name=name, **defaults)
            session.add(gc)
            await session.commit()
            await session.refresh(gc)
            return gc
    return _create
