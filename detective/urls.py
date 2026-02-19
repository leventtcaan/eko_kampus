from django.urls import path

from .views import DetectiveReportListCreateView

app_name = "detective"

urlpatterns = [
    path("reports/", DetectiveReportListCreateView.as_view(), name="list-create"),
]
