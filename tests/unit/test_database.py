"""Unit tests for the database helpers."""

import importlib
import os

import pytest
import sqlalchemy.ext.asyncio as sa_asyncio

from app import database
from app.config import settings


def test_normalize_database_url_strips_bad_params():
    raw = "postgresql://user:pass@localhost:5432/db?sslmode=require&target_session_attrs=read-write&keep=yes"
    normalized = database._normalize_database_url(raw)

    assert normalized.startswith("postgresql+asyncpg://")
    assert "sslmode" not in normalized
    assert "target_session_attrs" not in normalized
    assert "keep=yes" in normalized


def test_normalize_database_url_keeps_asyncpg_scheme():
    raw = "postgresql+asyncpg://user:pass@localhost/db"
    assert database._normalize_database_url(raw) == raw


def _reload_database_with(monkeypatch, *, url=None, use_ssl=None):
    """Reloads the module while stubbing engine/sessionmaker to capture args."""
    orig_engine = sa_asyncio.create_async_engine
    orig_sessionmaker = sa_asyncio.async_sessionmaker
    recorded: dict = {}

    def stub_engine(clean_url, echo=False, connect_args=None):
        recorded["clean_url"] = clean_url
        recorded["connect_args"] = connect_args
        return "engine"

    def stub_sessionmaker(*args, **kwargs):
        recorded["sessionmaker_args"] = (args, kwargs)
        return "sessionmaker"

    monkeypatch.setattr(sa_asyncio, "create_async_engine", stub_engine)
    monkeypatch.setattr(sa_asyncio, "async_sessionmaker", stub_sessionmaker)
    if url is not None:
        monkeypatch.setattr(settings, "database_url", url, raising=False)
    if use_ssl is not None:
        monkeypatch.setattr(settings, "database_use_ssl", use_ssl, raising=False)

    mod = importlib.reload(database)

    # restore to real functions before returning but keep our recorded data
    monkeypatch.setattr(sa_asyncio, "create_async_engine", orig_engine)
    monkeypatch.setattr(sa_asyncio, "async_sessionmaker", orig_sessionmaker)
    importlib.reload(database)
    return mod, recorded


def test_connect_args_include_user_permissions(monkeypatch):
    url = "postgresql://user.name:secret@host:5432/db?sslmode=require&foo=bar"
    mod, recorded = _reload_database_with(monkeypatch, url=url, use_ssl=True)

    assert recorded["clean_url"].startswith("postgresql+asyncpg://user.name:secret@host:5432/db")
    connect_args = recorded["connect_args"]
    assert connect_args["user"] == "user.name"
    assert connect_args["password"] == "secret"
    assert connect_args["ssl"] == "require"
    assert connect_args["statement_cache_size"] == 0
    assert mod._connect_args["user"] == "user.name"


def test_environment_variables_are_cleared(monkeypatch):
    keys = [
        "PGSSLMODE",
        "PGCHANNELBINDING",
        "PGGSSENCMODE",
        "PGTARGETSESSIONATTRS",
        "PGSSLNEGOTIATION",
    ]
    saved = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ[key] = "dirty"

    # reload with stubbed engine to avoid touching DB
    _ = _reload_database_with(monkeypatch, url=settings.database_url, use_ssl=settings.database_use_ssl)

    assert all(os.environ.get(key) is None for key in keys)

    for key, value in saved.items():
        if value is not None:
            os.environ[key] = value
        else:
            os.environ.pop(key, None)
