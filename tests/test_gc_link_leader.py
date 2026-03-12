"""Testes do vínculo de líderes em GCs."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.leader import Leader
from app.services.gc_service import GcService


@pytest.mark.asyncio
async def test_link_leader_returns_gc_reloaded_with_new_leader():
    """Após vincular um líder, o serviço deve retornar o GC recarregado com o novo líder."""
    gc_id = uuid.uuid4()
    leader_id = uuid.uuid4()

    old_gc = Gc(
        id=gc_id,
        name="GC Central",
        zip_code="13201000",
        street="Rua Teste",
        neighborhood="Centro",
        city="Jundiaí",
        state="SP",
        is_active=True,
    )
    old_gc.leader_associations = []

    leader = Leader(
        id=leader_id,
        name="Líder Teste",
        is_active=True,
    )
    leader.contacts = []

    updated_gc = Gc(
        id=gc_id,
        name="GC Central",
        zip_code="13201000",
        street="Rua Teste",
        neighborhood="Centro",
        city="Jundiaí",
        state="SP",
        is_active=True,
    )
    updated_gc.leader_associations = [
        GcLeader(gc_id=gc_id, leader_id=leader_id, gc=updated_gc, leader=leader)
    ]

    # Primeira chamada: verifica se o GC existe (deve retornar o gc_id)
    gc_exists_result = MagicMock()
    gc_exists_result.scalars.return_value.first.return_value = gc_id

    # Segunda chamada: verifica se o vínculo já existe (deve retornar None)
    link_exists_result = MagicMock()
    link_exists_result.scalars.return_value.first.return_value = None

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[gc_exists_result, link_exists_result])
    db.commit = AsyncMock()
    db.add = MagicMock()

    service = GcService(db)
    service.get_by_id = AsyncMock(return_value=updated_gc)

    result = await service.link_leader(gc_id, leader_id)

    assert result is updated_gc
    assert len(result.leaders) == 1
    assert result.leaders[0].id == leader_id
    assert result.leaders[0].name == "Líder Teste"
    service.get_by_id.assert_awaited_once_with(gc_id)
    db.commit.assert_awaited_once()
    db.add.assert_called_once()

