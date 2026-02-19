from django.contrib.auth import get_user_model

from rest_framework import generics, permissions

from .models import DetectiveReport, DetectiveReportStatus
from .serializers import DetectiveReportCreateSerializer, DetectiveReportListSerializer

User = get_user_model()


class DetectiveReportListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/detective/reports/  — Haritada gösterilecek aktif sorun bildirimlerini listeler.
    POST /api/detective/reports/  — Yeni bir çevre sorunu bildirimi oluşturur.
    """

    permission_classes = [permissions.AllowAny]
    queryset = DetectiveReport.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DetectiveReportCreateSerializer
        return DetectiveReportListSerializer

    def get_queryset(self):
        active_statuses = [
            DetectiveReportStatus.PENDING,
            DetectiveReportStatus.CONFIRMED,
        ]
        qs = (
            DetectiveReport.objects.filter(status__in=active_statuses)
            .select_related("reporter", "nearest_bin")
            .order_by("-created_at")
        )

        problem_type = self.request.query_params.get("problem_type")
        if problem_type:
            qs = qs.filter(problem_type=problem_type)

        try:
            limit = min(int(self.request.query_params.get("limit", 100)), 200)
        except (TypeError, ValueError):
            limit = 100

        return qs[:limit]

    def perform_create(self, serializer):
        reporter = (
            self.request.user
            if self.request.user.is_authenticated
            else User.objects.first()
        )
        serializer.save(reporter=reporter)
