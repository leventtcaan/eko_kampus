from django.urls import path

from .views import DetectiveReportCreateView, DetectiveReportListView

app_name = "detective"

urlpatterns = [
    path("", DetectiveReportListView.as_view(), name="list"),
    path("create/", DetectiveReportCreateView.as_view(), name="create"),
]
