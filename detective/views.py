from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DetectiveReport, DetectiveReportStatus
from .serializers import DetectiveReportCreateSerializer, DetectiveReportListSerializer


class DetectiveReportCreateView(APIView):
    """
    POST /api/detective/
    Yeni bir çevre sorunu bildirimi oluşturur.
    """

    def post(self, request):
        serializer = DetectiveReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save(reporter=request.user)

        return Response(
            DetectiveReportListSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )


class DetectiveReportListView(APIView):
    """
    GET /api/detective/
    Haritada gösterilmek üzere PENDING ve CONFIRMED durumundaki aktif
    sorun bildirimlerini listeler.

    Opsiyonel query parametreleri:
        ?problem_type=LITTERING   — türe göre filtrele
        ?limit=50                 — sayfa başına kayıt (max 200)
    """

    def get(self, request):
        active_statuses = [
            DetectiveReportStatus.PENDING,
            DetectiveReportStatus.CONFIRMED,
        ]
        qs = (
            DetectiveReport.objects.filter(status__in=active_statuses)
            .select_related("reporter", "nearest_bin")
            .order_by("-created_at")
        )

        problem_type = request.query_params.get("problem_type")
        if problem_type:
            qs = qs.filter(problem_type=problem_type)

        try:
            limit = min(int(request.query_params.get("limit", 100)), 200)
        except (TypeError, ValueError):
            limit = 100

        serializer = DetectiveReportListSerializer(qs[:limit], many=True)
        return Response(serializer.data)
