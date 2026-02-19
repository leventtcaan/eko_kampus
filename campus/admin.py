from django.contrib import admin

from .models import Bin, BinStatusLog, Building


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "building_type", "is_indoor", "is_active")
    list_filter = ("building_type", "is_indoor", "is_active")
    search_fields = ("name", "code")
    ordering = ("name",)


@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = (
        "code", "bin_type", "building", "fill_level", "fill_status",
        "status", "is_active", "last_emptied_at", "last_report_at",
    )
    list_filter = ("bin_type", "status", "is_active", "building__building_type")
    search_fields = ("code", "location_description", "building__name", "building__code")
    ordering = ("code",)
    readonly_fields = ("id", "fill_status", "created_at", "updated_at")

    @admin.display(description="Doluluk Durumu")
    def fill_status(self, obj):
        return obj.fill_status


@admin.register(BinStatusLog)
class BinStatusLogAdmin(admin.ModelAdmin):
    list_display = ("bin", "fill_level", "trigger", "triggered_by", "created_at")
    list_filter = ("trigger", "created_at")
    search_fields = ("bin__code", "triggered_by__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
