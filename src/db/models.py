from __future__ import annotations

import datetime as dt
from typing import Optional
from sqlalchemy import BigInteger, String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), default="en")
    minute_balance: Mapped[int] = mapped_column(Integer, default=0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    jobs: Mapped[list["Job"]] = relationship(back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    unlimited: Mapped[bool] = mapped_column(Boolean, default=False)
    max_jobs_per_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_minutes_per_job: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserPlan(Base):
    __tablename__ = "user_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    ends_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(32))  # voice|audio|video|youtube
    source_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    mode: Mapped[str] = mapped_column(String(16))  # full|summary|keypoints
    status: Mapped[str] = mapped_column(String(32), default="queued")
    duration_sec: Mapped[Optional[float]] = mapped_column()
    transcript_text: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    timestamps_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    summary_text: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    key_points_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    export_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="jobs")
    exports: Mapped[list["JobExport"]] = relationship(back_populates="job")

Index("ix_jobs_user_created", Job.user_id, Job.created_at)


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    ends_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime, nullable=True)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64))
    external_id: Mapped[str] = mapped_column(String(128))
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    status: Mapped[str] = mapped_column(String(32), default="created")
    raw_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


class JobExport(Base):
    __tablename__ = "job_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # txt|md
    content: Mapped[Text] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    job: Mapped[Job] = relationship(back_populates="exports")

