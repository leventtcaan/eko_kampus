from django.db.models import F
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bounty, BountyClaim, BountyStatus
from .serializers import BountyClaimCreateSerializer, BountySerializer


class BountyListView(APIView):
    """
    GET /api/bounties/
    Durumu OPEN ve son kullanma tarihi geçmemiş aktif görevleri listeler.

    Opsiyonel query parametreleri:
        ?bin=<bin_code>   — belirli bir kutuya ait görevler
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        qs = (
            Bounty.objects.filter(status=BountyStatus.OPEN, expires_at__gt=now)
            .select_related("target_bin")
            .order_by("expires_at")
        )

        bin_code = request.query_params.get("bin")
        if bin_code:
            qs = qs.filter(target_bin__code=bin_code)

        serializer = BountySerializer(qs, many=True)
        return Response(serializer.data)


class BountyClaimCreateView(APIView):
    """
    POST /api/bounties/claim/
    Kullanıcı bir görevi tamamlandı olarak işaretler.

    Beklenen body:
        {
            "bounty": "<uuid>",
            "qualifying_report": "<uuid>"   (opsiyonel)
        }

    İş mantığı:
        1. Serializer validasyonu (bounty açık mı? daha önce claim edildi mi?)
        2. BountyClaim oluşturulur.
        3. Bounty.current_claimants atomik olarak artırılır.
        4. Slot dolmuşsa bounty CLOSED yapılır.
    """

    def post(self, request):
        serializer = BountyClaimCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        bounty = serializer.validated_data["bounty"]

        claim = serializer.save(user=request.user)

        # current_claimants atomik artır.
        Bounty.objects.filter(pk=bounty.pk).update(
            current_claimants=F("current_claimants") + 1
        )
        bounty.refresh_from_db(fields=["current_claimants"])

        # Tüm slotlar doldu mu?
        if bounty.current_claimants >= bounty.max_claimants:
            Bounty.objects.filter(pk=bounty.pk).update(status=BountyStatus.CLOSED)

        return Response(
            {
                "id": str(claim.id),
                "bounty": str(bounty.id),
                "bounty_title": bounty.title,
                "status": claim.status,
                "claimed_at": claim.claimed_at,
            },
            status=status.HTTP_201_CREATED,
        )
