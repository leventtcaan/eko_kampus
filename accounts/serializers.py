from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

ALLOWED_DOMAINS = ("@ogr.akdeniz.edu.tr", "@akdeniz.edu.tr")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password")

    def validate_email(self, value):
        if not any(value.endswith(domain) for domain in ALLOWED_DOMAINS):
            raise serializers.ValidationError(
                "Sadece Akdeniz Üniversitesi öğrencileri kayıt olabilir."
            )
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
