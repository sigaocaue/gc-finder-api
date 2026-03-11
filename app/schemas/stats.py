"""Schemas de resposta para o módulo de estatísticas."""

from pydantic import BaseModel


class EntityCountsResponse(BaseModel):
    """Contagem de registros por entidade."""

    users: int
    leaders: int
    gcs: int
    meetings: int
    medias: int
    leader_contacts: int
