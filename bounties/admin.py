from django.contrib import admin

from .models import Bounty, BountyClaim


@admin.register(Bounty)
class BountyAdmin(admin.ModelAdmin):
    list_display = (
        "title", "bounty_type", "status", "reward_points",
        "current_claimants", "max_claimants", "slots_remaining", "expires_at", "created_at",
    )
    list_filter = ("bounty_type", "status", "created_at")
    search_fields = ("title", "description", "created_by__email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "current_claimants", "slots_remaining", "is_claimable")
    autocomplete_fields = ("target_bin", "created_by")

    @admin.display(description="Kalan Slot")
    def slots_remaining(self, obj):
        return obj.slots_remaining


@admin.register(BountyClaim)
class BountyClaimAdmin(admin.ModelAdmin):
    list_display = ("user", "bounty", "status", "points_awarded", "claimed_at", "awarded_at")
    list_filter = ("status", "claimed_at")
    search_fields = ("user__email", "bounty__title")
    ordering = ("-claimed_at",)
    readonly_fields = ("claimed_at",)
    autocomplete_fields = ("user", "bounty", "qualifying_report")
