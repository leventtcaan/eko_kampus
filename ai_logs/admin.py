from django.contrib import admin

from .models import AIAnalysisLog


@admin.register(AIAnalysisLog)
class AIAnalysisLogAdmin(admin.ModelAdmin):
    list_display = (
        "feature", "model_used", "user", "total_tokens",
        "cost_usd", "response_time_ms", "success", "created_at",
    )
    list_filter = ("feature", "model_used", "success", "created_at")
    search_fields = ("user__email", "feature", "model_used", "error_code")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "total_tokens")

    @admin.display(description="Toplam Token")
    def total_tokens(self, obj):
        return obj.total_tokens
