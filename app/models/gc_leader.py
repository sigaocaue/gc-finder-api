"""Modelo pivot GC-Líder (tabela associativa many-to-many)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GcLeader(Base):
    __tablename__ = "gc_leaders"

    # Chave primária composta
    gc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gcs.id"), primary_key=True
    )
    leader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leaders.id"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relacionamentos
    gc: Mapped["Gc"] = relationship("Gc", back_populates="leader_associations")
    leader: Mapped["Leader"] = relationship(
        "Leader", back_populates="gc_associations"
    )

    def __repr__(self) -> str:
        return (
            f"<GcLeader(gc_id={self.gc_id}, leader_id={self.leader_id}, "
            f"is_primary={self.is_primary})>"
        )
