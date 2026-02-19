from rest_framework import serializers

from .models import DetectiveReport


class DetectiveReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectiveReport
        fields = (
            "id",
            "problem_type",
            "latitude",
            "longitude",
            "image_path",
            # backend tarafından doldurulur
            "nearest_bin",
            "image_hash",
            "ai_problem_detected",
            "ai_problem_type_suggestion",
            "ai_confidence_score",
            "ai_raw_response",
            "confirmation_count",
            "status",
            "points_awarded",
            "created_at",
        )
        read_only_fields = (
            "id",
            "nearest_bin",
            "image_hash",
            "ai_problem_detected",
            "ai_problem_type_suggestion",
            "ai_confidence_score",
            "ai_raw_response",
            "confirmation_count",
            "status",
            "points_awarded",
            "created_at",
        )


class DetectiveReportListSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True)
    nearest_bin_code = serializers.CharField(
        source="nearest_bin.code", read_only=True, default=None
    )
    problem_type_display = serializers.CharField(
        source="get_problem_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = DetectiveReport
        fields = (
            "id",
            "problem_type",
            "problem_type_display",
            "status",
            "status_display",
            "latitude",
            "longitude",
            "nearest_bin_code",
            "confirmation_count",
            "reporter_email",
            "points_awarded",
            "created_at",
        )
        read_only_fields = fields
