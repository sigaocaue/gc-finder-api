"""Modelo de Mídia do GC (imagens, vídeos, posts do Instagram)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GcMedia(Base):
    __tablename__ = "gc_medias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gcs.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'image' | 'instagram_post' | 'video'
    url: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Índices
    __table_args__ = (
        Index("ix_gc_medias_gc_id", "gc_id"),
    )

    # Relacionamentos
    gc: Mapped["Gc"] = relationship("Gc", back_populates="medias")

    def __repr__(self) -> str:
        return f"<GcMedia(id={self.id}, gc_id={self.gc_id}, type={self.type})>"
