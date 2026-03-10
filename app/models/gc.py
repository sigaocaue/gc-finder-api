"""Modelo de GC (Grupo de Convivência)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Gc(Base):
    __tablename__ = "gcs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Endereço
    zip_code: Mapped[str] = mapped_column(
        String(9), nullable=False
    )  # Formato: 00000-000
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complement: Mapped[str | None] = mapped_column(String(100), nullable=True)
    neighborhood: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)

    # Coordenadas geográficas
    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Índices
    __table_args__ = (
        Index("ix_gcs_zip_code", "zip_code"),
        Index("ix_gcs_city", "city"),
        Index("ix_gcs_is_active", "is_active"),
    )

    # Relacionamentos
    leader_associations: Mapped[list["GcLeader"]] = relationship(
        "GcLeader", back_populates="gc", lazy="selectin"
    )
    meetings: Mapped[list["GcMeeting"]] = relationship(
        "GcMeeting", back_populates="gc", lazy="selectin"
    )
    medias: Mapped[list["GcMedia"]] = relationship(
        "GcMedia", back_populates="gc", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Gc(id={self.id}, name={self.name}, city={self.city})>"
