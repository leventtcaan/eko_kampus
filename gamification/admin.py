from django.contrib import admin

from .models import Badge, PointTransaction, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "badge_type", "required_points", "is_active")
    list_filter = ("badge_type", "is_active")
    search_fields = ("code", "name", "description")
    ordering = ("badge_type", "name")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "related_object_type", "awarded_at")
    list_filter = ("badge__badge_type", "awarded_at")
    search_fields = ("user__email", "badge__code", "badge__name")
    ordering = ("-awarded_at",)
    readonly_fields = ("awarded_at",)
    autocomplete_fields = ("user", "badge")


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user", "amount", "balance_after", "transaction_type",
        "related_object_type", "created_at",
    )
    list_filter = ("transaction_type", "created_at")
    search_fields = ("user__email", "note", "related_object_type")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "balance_after")
    autocomplete_fields = ("user",)
