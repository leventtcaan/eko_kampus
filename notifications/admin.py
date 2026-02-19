from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user", "notification_type", "title",
        "is_read", "is_pushed", "created_at",
    )
    list_filter = ("notification_type", "is_read", "is_pushed", "created_at")
    search_fields = ("user__email", "title", "body")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user",)
