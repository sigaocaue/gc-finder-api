"""Modelo de Líder de GC."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Leader(Base):
    __tablename__ = "leaders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relacionamento 1:N com contatos/redes sociais do líder
    contacts: Mapped[list["LeaderContact"]] = relationship(
        "LeaderContact", back_populates="leader", lazy="selectin"
    )

    # Relacionamento many-to-many com GC via tabela pivot gc_leaders
    gc_associations: Mapped[list["GcLeader"]] = relationship(
        "GcLeader", back_populates="leader", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Leader(id={self.id}, name={self.name})>"
