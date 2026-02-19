from django.contrib import admin

from .models import SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "value_type", "updated_at")
    list_filter = ("value_type",)
    search_fields = ("key", "description")
    ordering = ("key",)
    readonly_fields = ("updated_at",)
