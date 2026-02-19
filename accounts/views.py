from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from detective.models import DetectiveReport
from reports.models import WasteReport
from .serializers import RegisterSerializer


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
