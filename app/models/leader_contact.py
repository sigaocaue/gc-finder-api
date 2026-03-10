"""Modelo de Contato/Rede Social do Líder."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeaderContact(Base):
    __tablename__ = "leader_contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    leader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leaders.id"), nullable=False
    )
    # Tipo do contato: 'whatsapp', 'instagram', 'facebook', 'email', 'twitter', etc.
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Valor do contato: número, @usuario, URL, endereço de e-mail, etc.
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    # Rótulo opcional para exibição (ex: "WhatsApp pessoal", "Instagram do ministério")
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_leader_contacts_leader_id", "leader_id"),
    )

    # Relacionamentos
    leader: Mapped["Leader"] = relationship("Leader", back_populates="contacts")

    def __repr__(self) -> str:
        return f"<LeaderContact(id={self.id}, leader_id={self.leader_id}, type={self.type})>"
