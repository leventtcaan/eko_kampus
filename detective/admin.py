from django.contrib import admin

from .models import DetectiveReport, DetectiveVote


@admin.register(DetectiveReport)
class DetectiveReportAdmin(admin.ModelAdmin):
    list_display = (
        "problem_type", "status", "reporter", "confirmation_count",
        "nearest_bin", "points_awarded", "resolved_by", "created_at",
    )
    list_filter = ("problem_type", "status", "created_at")
    search_fields = ("reporter__email", "nearest_bin__code")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "confirmation_count", "ai_problem_detected",
        "ai_problem_type_suggestion", "ai_confidence_score",
        "ai_raw_response", "created_at",
    )
    autocomplete_fields = ("reporter", "nearest_bin", "resolved_by")


@admin.register(DetectiveVote)
class DetectiveVoteAdmin(admin.ModelAdmin):
    list_display = ("voter", "detective_report", "vote", "voter_distance_meters", "created_at")
    list_filter = ("vote", "created_at")
    search_fields = ("voter__email",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
