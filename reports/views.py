from django.contrib.auth import get_user_model

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()

from .models import WasteReport
from .serializers import WasteReportCreateSerializer, WasteReportDetailSerializer


class WasteReportCreateView(APIView):
    """
    POST /api/reports/
    Yeni bir 'çöp atma' bildirimi oluşturur.

    İş mantığı:
        1. Frekans kilidi: Aynı kullanıcı + aynı kutu ikilisi
           son RATE_LOCK_MINUTES dakika içinde bildirim yaptıysa → 400.
        2. Serializer doğrulaması.
        3. Rapor kaydedilir; user ve status backend tarafından atanır.

    Sonraki aşamada eklenecekler (şimdilik atlanıyor):
        - Geo-fence kontrolü (kullanıcı koordinatı ile kutu mesafesi)
        - Time-spoofing kontrolü (client_timestamp farkı)
        - Suspicion score hesabı
        - fill_delta hesabı ve Bin.add_fill() çağrısı
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = WasteReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save(
            user=request.user if request.user.is_authenticated else User.objects.first(),
            status=WasteReport.ReportStatus.PENDING if hasattr(WasteReport, "ReportStatus") else "PENDING",
        )

        return Response(
            WasteReportDetailSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class WasteReportListView(APIView):
    """
    GET /api/reports/
    Giriş yapmış kullanıcının kendi raporlarını listeler.
    """

    permission_classes = [permissions.AllowAny]

    def get_queryset(self, request):
        if request.user.is_anonymous:
            effective_user = User.objects.first()
            if effective_user is None:
                return WasteReport.objects.none()
            return (
                WasteReport.objects.filter(user=effective_user)
                .select_related("bin", "photo_evidence")
                .order_by("-created_at")[:50]
            )
        return (
            WasteReport.objects.filter(user=request.user)
            .select_related("bin", "photo_evidence")
            .order_by("-created_at")[:50]
        )

    def get(self, request):
        serializer = WasteReportDetailSerializer(self.get_queryset(request), many=True)
        return Response(serializer.data)
