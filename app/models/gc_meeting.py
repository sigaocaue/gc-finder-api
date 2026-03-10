"""Modelo de Reunião/Encontro do GC."""

import uuid
from datetime import datetime, time

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GcMeeting(Base):
    __tablename__ = "gc_meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gcs.id"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
    )  # 0=Domingo, 1=Segunda, ..., 6=Sábado
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Índices
    __table_args__ = (
        Index("ix_gc_meetings_gc_id", "gc_id"),
    )

    # Relacionamentos
    gc: Mapped["Gc"] = relationship("Gc", back_populates="meetings")

    def __repr__(self) -> str:
        return (
            f"<GcMeeting(id={self.id}, gc_id={self.gc_id}, "
            f"weekday={self.weekday}, start_time={self.start_time})>"
        )
