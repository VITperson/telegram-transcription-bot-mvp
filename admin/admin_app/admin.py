from __future__ import annotations

from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import User, Job, Plan, UserPlan, PromoCode, Payment, JobExport


@admin.action(description="Export selected to CSV")
def export_as_csv(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta}.csv'
    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
    return response


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "minute_balance", "locale", "created_at")
    search_fields = ("id", "username")
    actions = [export_as_csv]

    @admin.action(description="Top up 10 minutes")
    def topup_10(self, request, queryset):
        for user in queryset:
            user.minute_balance += 10
        # managed=False prevents save(); this is placeholder for manual SQL or separate API


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "source_type", "mode", "status", "created_at")
    list_filter = ("source_type", "mode", "status")
    search_fields = ("id", "user__id")
    actions = [export_as_csv]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "unlimited", "active")
    actions = [export_as_csv]


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "plan", "started_at", "ends_at")
    actions = [export_as_csv]


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "minutes", "used_count", "active")
    actions = [export_as_csv]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "provider", "status", "amount_cents", "created_at")
    actions = [export_as_csv]


@admin.register(JobExport)
class JobExportAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "kind", "created_at")
    actions = [export_as_csv]

