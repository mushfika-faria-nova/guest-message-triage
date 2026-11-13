"""Database tables. SQLAlchemy 2.0 typed models, like JPA @Entity classes."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# The original message is kept: whoever handles a needs_review message has to read it.
class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    sender: Mapped[str | None]
    needs_review: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tickets: Mapped[list["TicketRow"]] = relationship(back_populates="message")


class TicketRow(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Postgres doesn't index foreign keys on its own, so index=True.
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    # Plain text, not a Postgres enum: Pydantic already checks the values, and a new
    # category then needs no migration.
    category: Mapped[str]
    urgency: Mapped[str]
    unit: Mapped[str | None]
    next_action: Mapped[str]

    message: Mapped[MessageRow] = relationship(back_populates="tickets")
