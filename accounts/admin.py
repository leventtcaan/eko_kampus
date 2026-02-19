from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserTrustLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email", "username", "get_full_name", "role",
        "trust_score", "total_points", "is_active", "created_at",
    )
    list_filter = ("role", "is_active", "is_staff", "department")
    search_fields = ("email", "username", "first_name", "last_name", "student_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "total_points")

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (_("Kişisel Bilgiler"), {"fields": ("first_name", "last_name", "student_id", "department")}),
        (_("Rol ve Puanlama"), {"fields": ("role", "trust_score", "total_points")}),
        (_("İzinler"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Önemli Tarihler"), {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(UserTrustLog)
class UserTrustLogAdmin(admin.ModelAdmin):
    list_display = ("user", "delta", "score_after", "reason", "related_object_type", "created_at")
    list_filter = ("reason", "created_at")
    search_fields = ("user__email", "user__username", "related_object_type")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
