from django.contrib import admin

from .models import PhotoEvidence, VettingVote, WasteReport


class PhotoEvidenceInline(admin.StackedInline):
    model = PhotoEvidence
    extra = 0
    readonly_fields = (
        "image_hash", "ai_bin_detected", "ai_waste_detected",
        "ai_category_suggestion", "ai_confidence_score",
        "ai_is_stock_photo", "ai_analyzed_at", "created_at",
    )


class VettingVoteInline(admin.TabularInline):
    model = VettingVote
    extra = 0
    readonly_fields = ("voter", "vote", "voter_trust_at_vote", "voter_distance_meters", "created_at")


@admin.register(WasteReport)
class WasteReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "bin", "waste_category", "verification_method",
        "status", "suspicion_score", "points_awarded", "created_at",
    )
    list_filter = ("status", "waste_category", "verification_method", "created_at")
    search_fields = ("user__email", "bin__code")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "geo_distance_meters", "fill_delta",
        "suspicion_score", "created_at",
    )
    inlines = (PhotoEvidenceInline, VettingVoteInline)
    autocomplete_fields = ("user", "bin")

    @admin.display(boolean=True, description="Yüksek Şüpheli?")
    def is_high_suspicion(self, obj):
        return obj.is_high_suspicion


@admin.register(PhotoEvidence)
class PhotoEvidenceAdmin(admin.ModelAdmin):
    list_display = (
        "report", "ai_bin_detected", "ai_waste_detected",
        "ai_category_suggestion", "ai_confidence_score",
        "ai_is_stock_photo", "ai_analyzed_at",
    )
    list_filter = ("ai_bin_detected", "ai_waste_detected", "ai_is_stock_photo")
    search_fields = ("report__id", "image_hash", "ai_category_suggestion")
    ordering = ("-created_at",)
    readonly_fields = (
        "image_hash", "ai_bin_detected", "ai_waste_detected",
        "ai_category_suggestion", "ai_confidence_score",
        "ai_is_stock_photo", "ai_raw_response", "ai_analyzed_at", "created_at",
    )


@admin.register(VettingVote)
class VettingVoteAdmin(admin.ModelAdmin):
    list_display = ("voter", "report", "vote", "voter_trust_at_vote", "voter_distance_meters", "created_at")
    list_filter = ("vote", "created_at")
    search_fields = ("voter__email", "report__id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
