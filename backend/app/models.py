from datetime import date, datetime, timezone

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(50))
    industry: Mapped[str] = mapped_column(String(80), default="")
    tenure: Mapped[str] = mapped_column(String(20))
    fears: Mapped[list] = mapped_column(JSON, default=list)
    fear_note: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Case(Base):
    """One situation a user works through. inputs/result are snapshots (JSON) of what the user
    entered and what the deterministic engine calculated at that time."""
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint("status IN ('draft','decided')", name="ck_cases_status"),
        CheckConstraint("confidence_before BETWEEN 1 AND 5", name="ck_cases_confidence"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    situation_id: Mapped[str] = mapped_column(String(80))
    inputs: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    confidence_before: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | decided
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    decision: Mapped["Decision | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")
    reflection: Mapped["Reflection | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")
    followup: Mapped["FollowUp | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")


class Decision(Base):
    """The option the user chose and the Change Request document generated from it (one per case)."""
    __tablename__ = "decisions"
    __table_args__ = (CheckConstraint("option IN ('accept','defer','decline')", name="ck_decisions_option"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    option: Mapped[str] = mapped_column(String(20))
    rationale: Mapped[str] = mapped_column(Text, default="")
    document: Mapped[str] = mapped_column(Text)
    followup_due: Mapped[date] = mapped_column(Date)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reflection(Base):
    """What the user learned, with confidence after (compared with Case.confidence_before)."""
    __tablename__ = "reflections"
    __table_args__ = (CheckConstraint("confidence_after BETWEEN 1 AND 5", name="ck_reflections_confidence"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    learned: Mapped[str] = mapped_column(Text, default="")
    different: Mapped[str] = mapped_column(Text, default="")
    confidence_after: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class FollowUp(Base):
    """What happened afterwards, as reported by the user (not verified)."""
    __tablename__ = "followups"
    __table_args__ = (CheckConstraint("outcome IN ('worked','partly','not_yet','not_applied')", name="ck_followups_outcome"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    outcome: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class JournalEntry(Base):
    __tablename__ = "journal"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=True)
    type: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
