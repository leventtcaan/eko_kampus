import base64

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import serializers

from config.models import SystemSetting
from .models import PhotoEvidence, ReportStatus, WasteReport
from .services import validate_waste_with_ai

User = get_user_model()


class PhotoEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoEvidence
        fields = (
            "image_path",
            # AI ve hash alanları salt okunur — backend doldurur.
            "image_hash",
            "ai_bin_detected",
            "ai_waste_detected",
            "ai_category_suggestion",
            "ai_confidence_score",
            "ai_is_stock_photo",
            "ai_analyzed_at",
            "created_at",
        )
        read_only_fields = (
            "image_hash",
            "ai_bin_detected",
            "ai_waste_detected",
            "ai_category_suggestion",
            "ai_confidence_score",
            "ai_is_stock_photo",
            "ai_analyzed_at",
            "created_at",
        )


class WasteReportCreateSerializer(serializers.ModelSerializer):
    """
    Mobil uygulamanın 'çöp attım' bildirimini oluşturmak için kullandığı serializer.

    Kullanıcının göndereceği alanlar:
        bin, waste_category, verification_method,
        latitude, longitude, client_timestamp

    Backend'in otomatik dolduracağı (read_only) alanlar:
        user, geo_distance_meters, fill_delta,
        suspicion_score, status, points_awarded, id
    """

    photo_evidence = PhotoEvidenceSerializer(required=False)
    photo_base64 = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = WasteReport
        fields = (
            "id",
            "bin",
            "waste_category",
            "verification_method",
            "latitude",
            "longitude",
            "client_timestamp",
            "photo_evidence",
            "photo_base64",
            # Read-only — backend tarafından hesaplanır veya atanır.
            "geo_distance_meters",
            "fill_delta",
            "suspicion_score",
            "status",
            "points_awarded",
            "created_at",
        )
        read_only_fields = (
            "id",
            "geo_distance_meters",
            "fill_delta",
            "suspicion_score",
            "status",
            "points_awarded",
            "created_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        effective_user = (
            request.user
            if (request and request.user.is_authenticated)
            else User.objects.first()
        )
        if effective_user is None:
            return attrs

        rate_lock_minutes = SystemSetting.get("RATE_LOCK_MINUTES", default=1)
        cutoff = timezone.now() - timezone.timedelta(minutes=rate_lock_minutes)

        duplicate = WasteReport.objects.filter(
            user=effective_user,
            bin=attrs.get("bin"),
            waste_category=attrs.get("waste_category"),
            client_timestamp__gte=cutoff,
        ).exists()

        if duplicate:
            raise serializers.ValidationError(
                f"Bu kutuya aynı atık türünü son {rate_lock_minutes} dakika içinde zaten bildirdiniz."
            )

        photo = attrs.get("photo_base64")
        waste_category = attrs.get("waste_category")
        if photo and waste_category:
            image_bytes = photo.encode("utf-8") if isinstance(photo, str) else photo.read()
            base64_str = base64.b64encode(image_bytes).decode("utf-8") if not isinstance(photo, str) else photo
            if hasattr(photo, "seek"):
                photo.seek(0)
            is_valid = validate_waste_with_ai(base64_str, waste_category)
            if not is_valid:
                raise serializers.ValidationError(
                    {"photo": "Yapay Zeka Reddi: Görseldeki nesne seçilen atık türüyle eşleşmiyor!"}
                )

        return attrs

    def create(self, validated_data):
        photo_base64 = validated_data.pop("photo_base64", None)
        validated_data.pop("photo_evidence", None)  # reverse relation, ayrıca işlenmez

        if photo_base64:
            validated_data["status"] = ReportStatus.APPROVED

        return WasteReport.objects.create(**validated_data)


class WasteReportDetailSerializer(serializers.ModelSerializer):
    """Rapor detay ve liste görünümü için."""

    photo_evidence = PhotoEvidenceSerializer(read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    bin_code = serializers.CharField(source="bin.code", read_only=True)

    class Meta:
        model = WasteReport
        fields = (
            "id",
            "user_email",
            "bin_code",
            "waste_category",
            "verification_method",
            "latitude",
            "longitude",
            "geo_distance_meters",
            "fill_delta",
            "suspicion_score",
            "status",
            "points_awarded",
            "client_timestamp",
            "created_at",
            "photo_evidence",
        )
        read_only_fields = fields
