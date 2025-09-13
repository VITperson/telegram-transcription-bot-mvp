from __future__ import annotations

from django.db import models


class User(models.Model):
    id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    locale = models.CharField(max_length=8, default="en")
    minute_balance = models.IntegerField(default=0)
    is_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "users"
        managed = False

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.id} @{self.username or ''}".strip()


class Plan(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    unlimited = models.BooleanField(default=False)
    max_jobs_per_day = models.IntegerField(null=True)
    max_minutes_per_job = models.IntegerField(null=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "plans"
        managed = False


class UserPlan(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    started_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "user_plans"
        managed = False


class Job(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    source_type = models.CharField(max_length=32)
    source_link = models.TextField(null=True)
    language = models.CharField(max_length=16, null=True)
    mode = models.CharField(max_length=16)
    status = models.CharField(max_length=32)
    duration_sec = models.FloatField(null=True)
    transcript_text = models.TextField(null=True)
    timestamps_json = models.JSONField(null=True)
    summary_text = models.TextField(null=True)
    key_points_json = models.JSONField(null=True)
    export_ready = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "jobs"
        managed = False


class PromoCode(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=64, unique=True)
    minutes = models.IntegerField(default=0)
    starts_at = models.DateTimeField(null=True)
    ends_at = models.DateTimeField(null=True)
    max_uses = models.IntegerField(null=True)
    used_count = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "promo_codes"
        managed = False


class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    provider = models.CharField(max_length=64)
    external_id = models.CharField(max_length=128)
    amount_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=32, default="created")
    raw_payload = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "payments"
        managed = False


class JobExport(models.Model):
    id = models.AutoField(primary_key=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    kind = models.CharField(max_length=16)
    content = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "job_exports"
        managed = False

