import base64
import uuid

from django.core.files.base import ContentFile

from rest_framework import serializers

from .models import DetectiveReport


class DetectiveReportCreateSerializer(serializers.ModelSerializer):
    photo_base64 = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = DetectiveReport
        fields = (
            "id",
            "problem_type",
            "description",
            "latitude",
            "longitude",
            "photo",
            "photo_base64",
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
            "photo",
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

    def create(self, validated_data):
        photo_base64 = validated_data.pop("photo_base64", None)

        if photo_base64:
            image_data = base64.b64decode(photo_base64)
            file_name = f"{uuid.uuid4()}.jpg"
            validated_data["photo"] = ContentFile(image_data, name=file_name)

        return DetectiveReport.objects.create(**validated_data)


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
            "description",
            "photo",
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
