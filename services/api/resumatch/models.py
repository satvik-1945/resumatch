import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from resumatch.db import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    weekly_target: Mapped[int] = mapped_column(default=3, server_default="3")
    __table_args__ = (
        CheckConstraint("weekly_target BETWEEN 1 AND 14", name="weekly_target_range"),
    )


class Login(Base):
    __tablename__ = "logins"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OutreachSession(Base):
    __tablename__ = "outreach_sessions"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    intention: Mapped[str] = mapped_column(String(200))
    target_minutes: Mapped[int] = mapped_column(default=25)
    state: Mapped[str] = mapped_column(String(20), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    running_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(default=0, server_default="0")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("state IN ('active','paused','review','completed')", name="session_state"),
        CheckConstraint("elapsed_seconds >= 0", name="session_elapsed"),
        CheckConstraint("target_minutes BETWEEN 5 AND 180", name="session_target"),
        Index("one_open_session", "user_id", unique=True,
              postgresql_where=text("state != 'completed'")),
    )


class Capture(Base):
    __tablename__ = "captures"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outreach_sessions.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column()
    source: Mapped[str] = mapped_column(String(20))
    original: Mapped[dict] = mapped_column(JSONB)
    details: Mapped[dict] = mapped_column(JSONB)
    decision: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    followup_done: Mapped[bool] = mapped_column(default=False, server_default="false")
    analysis: Mapped[dict | None] = mapped_column(JSONB)
    __table_args__ = (
        Index("capture_request_once", "session_id", "request_id", unique=True),
        CheckConstraint("decision IN ('pending','approved','discarded')", name="capture_decision"),
        CheckConstraint("source IN ('manual','browser')", name="capture_source"),
    )


class Pairing(Base):
    __tablename__ = "extension_pairings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    extension_id: Mapped[str] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionEvent(Base):
    __tablename__ = "session_events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outreach_sessions.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionRecap(Base):
    __tablename__ = "session_recaps"
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("outreach_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    payload: Mapped[dict] = mapped_column(JSONB)
    reflection: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
