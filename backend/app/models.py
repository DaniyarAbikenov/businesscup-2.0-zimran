from datetime import date, datetime, timezone

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
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
    email_reminders: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # opt-in, never on by default
    day7_nudge_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    seeded: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")  # demo sample data, not counted for the free limit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    decision: Mapped["Decision | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")
    reflection: Mapped["Reflection | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")
    followup: Mapped["FollowUp | None"] = relationship(uselist=False, cascade="all, delete-orphan", lazy="selectin")
    documents: Mapped[list["Document"]] = relationship(cascade="all, delete-orphan", lazy="selectin", order_by="Document.id")


class Decision(Base):
    """The option the user chose and the document generated from it (one per case). Allowed option keys
    come from the situation pack and are checked by the API; the database only checks the key format."""
    __tablename__ = "decisions"
    __table_args__ = (CheckConstraint("option ~ '^[a-z][a-z_]{0,19}$'", name="ck_decisions_option"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    option: Mapped[str] = mapped_column(String(20))
    rationale: Mapped[str] = mapped_column(Text, default="")
    document: Mapped[str] = mapped_column(Text)
    followup_due: Mapped[date] = mapped_column(Date)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class Document(Base):
    """Anything the user writes or saves for a case: the Change Request (starts as the generated text,
    then edited by the user) and the client message. One current text per (case, kind);
    every saved change is kept in DocumentRevision."""
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("kind IN ('change_request','client_message')", name="ck_documents_kind"),
        UniqueConstraint("case_id", "kind", name="uq_documents_case_kind"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revisions: Mapped[list["DocumentRevision"]] = relationship(cascade="all, delete-orphan", order_by="DocumentRevision.id")


class DocumentRevision(Base):
    __tablename__ = "document_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), default="user")  # generated | ai | user
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Purchase(Base):
    """A paid (or test-paid) pass. Active while expires_at is in the future."""
    __tablename__ = "purchases"
    __table_args__ = (
        CheckConstraint("provider IN ('test','stripe')", name="ck_purchases_provider"),
        CheckConstraint("amount_cents >= 0", name="ck_purchases_amount"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan: Mapped[str] = mapped_column(String(30))
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="usd")
    provider: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CustomSituation(Base):
    """A situation a user made from their own description: a validated preset on an existing engine.
    Only the owner can see or use it. Cases refer to it by id "my-<slug>"."""
    __tablename__ = "custom_situations"
    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_custom_situations_user_slug"),
        CheckConstraint("slug ~ '^[a-z0-9][a-z0-9-]{0,39}$'", name="ck_custom_situations_slug"),
        CheckConstraint("source IN ('ai')", name="ck_custom_situations_source"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(40))
    engine: Mapped[str] = mapped_column(String(30))
    preset: Mapped[dict] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(String(10), default="ai", server_default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EmailToken(Base):
    """One-click links in emails: record an outcome, or turn reminders off. Only the hash is stored; each link
    works once (unsubscribe may be repeated) and expires."""
    __tablename__ = "email_tokens"
    __table_args__ = (CheckConstraint("kind IN ('worked','partly','not_yet','unsubscribe')", name="ck_email_tokens_kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
