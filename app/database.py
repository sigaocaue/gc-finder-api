import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Parâmetros que o asyncpg não reconhece e precisam ser removidos da URL
_STRIP_PARAMS = {"sslmode", "ssl", "channel_binding", "gssencmode", "target_session_attrs", "sslnegotiation"}


def _normalize_database_url(raw_database_url: str) -> str:
    """Remove parâmetros incompatíveis com asyncpg e garante o driver correto."""
    parsed = urlparse(raw_database_url)
    query = parse_qs(parsed.query)

    clean_query = {k: v[0] for k, v in query.items() if k not in _STRIP_PARAMS}

    scheme = parsed.scheme
    if scheme.startswith("postgresql") and "+asyncpg" not in scheme:
        scheme = "postgresql+asyncpg"

    return urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        urlencode(clean_query) if clean_query else "",
        "",
    ))


# Variáveis libpq que conflitam com asyncpg
for key in ("PGSSLMODE", "PGCHANNELBINDING", "PGGSSENCMODE", "PGTARGETSESSIONATTRS", "PGSSLNEGOTIATION"):
    os.environ.pop(key, None)

_clean_url = _normalize_database_url(settings.database_url)

# Extrai user/password da URL original para evitar problemas com usernames contendo pontos (ex: Supabase pooler)
_parsed = urlparse(settings.database_url)
_connect_args: dict = {"statement_cache_size": 0}
if _parsed.username:
    _connect_args["user"] = _parsed.username
if _parsed.password:
    _connect_args["password"] = _parsed.password
if settings.database_use_ssl:
    _connect_args["ssl"] = "require"

engine = create_async_engine(_clean_url, echo=False, connect_args=_connect_args)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
