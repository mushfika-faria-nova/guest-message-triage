"""Database tables. SQLAlchemy 2.0 typed models, like JPA @Entity classes."""

import os
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, ForeignKey, create_engine, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from guest_message_triage.triage import TriageResult


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


# One engine (connection pool) for the whole app, like a DataSource bean.
# pool_pre_ping checks a connection before using it, so a DB restart doesn't
# break the next request.
@lru_cache
def get_engine() -> Engine:
    return create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)


# One session per request, closed when the request ends: the request-scoped
# EntityManager. yield hands it to the endpoint; the with-block closes it after.
def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def save_triage(session: Session, text: str, sender: str | None, result: TriageResult) -> MessageRow:
    """Save the message and its tickets in one transaction."""
    row = MessageRow(
        text=text,
        sender=sender,
        needs_review=result.needs_review,
        tickets=[TicketRow(**t.model_dump()) for t in result.tickets],
    )
    session.add(row)
    session.commit()
    return row
