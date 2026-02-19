from django.urls import path

from .views import TaskListAPIView, WasteReportCreateView, WasteReportListView

app_name = "reports"

urlpatterns = [
    path("", WasteReportListView.as_view(), name="list"),
    path("create/", WasteReportCreateView.as_view(), name="create"),
    path("tasks/", TaskListAPIView.as_view(), name="tasks"),
]
