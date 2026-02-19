from django.urls import path

from .views import WasteReportCreateView, WasteReportListView

app_name = "reports"

urlpatterns = [
    path("", WasteReportListView.as_view(), name="list"),
    path("create/", WasteReportCreateView.as_view(), name="create"),
]
