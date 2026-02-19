from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()

from detective.models import DetectiveReport
from .models import WasteReport
from .serializers import WasteReportCreateSerializer, WasteReportDetailSerializer


class WasteReportCreateView(APIView):
    """
    POST /api/reports/create/
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

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WasteReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save(
            user=request.user,
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

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        return (
            WasteReport.objects.filter(user=request.user)
            .select_related("bin", "photo_evidence")
            .order_by("-created_at")[:50]
        )

    def get(self, request):
        serializer = WasteReportDetailSerializer(self.get_queryset(request), many=True)
        return Response(serializer.data)


class TaskListAPIView(APIView):
    """
    GET /api/reports/tasks/
    Kullanıcının bugünkü ilerlemesiyle birlikte statik görev listesini döner.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        effective_user = request.user

        today = timezone.now().date()

        if effective_user:
            plastic_count = WasteReport.objects.filter(
                user=effective_user,
                waste_category="PLASTIC",
                created_at__date=today,
            ).count()
            paper_count = WasteReport.objects.filter(
                user=effective_user,
                waste_category="PAPER",
                created_at__date=today,
            ).count()
            detective_count = DetectiveReport.objects.filter(
                reporter=effective_user,
                created_at__date=today,
            ).count()
        else:
            plastic_count = paper_count = detective_count = 0

        tasks = [
            {
                "id": 1,
                "title": "Plastik Avcısı",
                "desc": "Bugün 3 plastik atık bildir.",
                "target": 3,
                "current": plastic_count,
                "reward": 50,
                "icon": "♻️",
            },
            {
                "id": 2,
                "title": "Çevre Dedektifi",
                "desc": "Kampüste 1 çevre sorunu bildir.",
                "target": 1,
                "current": detective_count,
                "reward": 100,
                "icon": "🕵️",
            },
            {
                "id": 3,
                "title": "Kağıt Tasarrufu",
                "desc": "Bugün 2 kağıt atık bildir.",
                "target": 2,
                "current": paper_count,
                "reward": 30,
                "icon": "📄",
            },
        ]

        return Response(tasks)
