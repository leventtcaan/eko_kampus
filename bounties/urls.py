from django.urls import path

from .views import BountyClaimCreateView, BountyListView

app_name = "bounties"

urlpatterns = [
    path("", BountyListView.as_view(), name="list"),
    path("claim/", BountyClaimCreateView.as_view(), name="claim"),
]
