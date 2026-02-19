from django.utils import timezone
from rest_framework import serializers

from .models import Bounty, BountyClaim


class BountySerializer(serializers.ModelSerializer):
    bounty_type_display = serializers.CharField(
        source="get_bounty_type_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    target_bin_code = serializers.CharField(
        source="target_bin.code", read_only=True, default=None
    )
    slots_remaining = serializers.IntegerField(read_only=True)
    is_claimable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Bounty
        fields = (
            "id",
            "title",
            "description",
            "bounty_type",
            "bounty_type_display",
            "status",
            "status_display",
            "reward_points",
            "max_claimants",
            "current_claimants",
            "slots_remaining",
            "is_claimable",
            "required_waste_category",
            "min_reports_required",
            "target_bin_code",
            "target_latitude",
            "target_longitude",
            "target_radius_meters",
            "expires_at",
            "created_at",
        )
        read_only_fields = fields


class BountyClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BountyClaim
        fields = (
            "id",
            "bounty",
            "qualifying_report",
            # backend tarafından doldurulur
            "status",
            "points_awarded",
            "claimed_at",
            "awarded_at",
        )
        read_only_fields = (
            "id",
            "status",
            "points_awarded",
            "claimed_at",
            "awarded_at",
        )

    def validate(self, attrs):
        user = self.context["request"].user
        bounty = attrs["bounty"]

        if not bounty.is_claimable:
            raise serializers.ValidationError(
                {"bounty": "Bu görev artık talep edilemiyor (kapalı veya süresi dolmuş)."}
            )

        if bounty.expires_at < timezone.now():
            raise serializers.ValidationError(
                {"bounty": "Bu görevin süresi dolmuş."}
            )

        already_claimed = BountyClaim.objects.filter(
            bounty=bounty, user=user
        ).exists()
        if already_claimed:
            raise serializers.ValidationError(
                {"bounty": "Bu görevi daha önce talep ettiniz."}
            )

        qualifying_report = attrs.get("qualifying_report")
        if qualifying_report and qualifying_report.user != user:
            raise serializers.ValidationError(
                {"qualifying_report": "Bu bildirim size ait değil."}
            )

        return attrs
