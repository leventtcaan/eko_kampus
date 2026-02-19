from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from detective.models import DetectiveReport
from reports.models import WasteReport
from .serializers import RegisterSerializer

User = get_user_model()


class RegisterView(CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        waste_count = WasteReport.objects.filter(user=user).count()
        issue_count = DetectiveReport.objects.filter(reporter=user).count()

        return Response({
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "waste_count": waste_count,
            "issue_count": issue_count,
        })


class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        users = User.objects.all()
        leaderboard = []

        for user in users:
            waste_count = WasteReport.objects.filter(user=user).count()
            issue_count = DetectiveReport.objects.filter(reporter=user).count()
            points = (waste_count * 10) + (issue_count * 50)
            if points > 0:
                leaderboard.append({
                    "id": user.id,
                    "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                    "points": points,
                })

        leaderboard.sort(key=lambda x: x["points"], reverse=True)
        leaderboard = leaderboard[:10]

        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return Response(leaderboard)
