from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202409130001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("minute_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unlimited", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_jobs_per_day", sa.Integer(), nullable=True),
        sa.Column("max_minutes_per_job", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "user_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id")),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_link", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("duration_sec", sa.Float(), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("timestamps_json", sa.JSON(), nullable=True),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("key_points_json", sa.JSON(), nullable=True),
        sa.Column("export_ready", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_jobs_user_created", "jobs", ["user_id", "created_at"]) 

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), unique=True, index=True),
        sa.Column("minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "job_exports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), index=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("job_exports")
    op.drop_table("payments")
    op.drop_table("promo_codes")
    op.drop_index("ix_jobs_user_created", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("user_plans")
    op.drop_table("plans")
    op.drop_table("users")

