# =============================================================================
# accounts/models.py
#
# Django App: accounts
# Bağımlılıklar: django.contrib.auth
#
# Bu app projenin tüm kullanıcı kimliği mantığını barındırır.
# Master Plan kuralı: İlk `migrate`'ten ÖNCE AbstractUser'dan türetilmiş
# custom user model oluşturulmalı. Bu dosyayı settings.py'de
# AUTH_USER_MODEL = 'accounts.User' olarak tanımla.
# =============================================================================

from __future__ import annotations

import uuid
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    """
    Sistemdeki kullanıcı rolleri.
    STUDENT: Bildiri yapan, puan kazanan öğrenci.
    STAFF:   Temizlik personeli — boşaltma kaydeder, bounty oluşturur.
    ADMIN:   Sistem yöneticisi — tüm yetkiler.
    """

    STUDENT = "STUDENT", _("Öğrenci")
    STAFF = "STAFF", _("Personel")
    ADMIN = "ADMIN", _("Yönetici")


class User(AbstractUser):
    """
    Projenin merkezi kullanıcı modeli.

    AbstractUser'dan türetildiği için Django'nun tüm auth mekanizmaları
    (login, logout, permission, session) hazır gelir.

    Ekstra alanlar:
    - student_id: Üniversite numarası; liderlik tablosu ve Çevre Karnesi için.
    - department: Bölüm bazlı ısı haritası analizleri için.
    - trust_score: Suistimal önleme sisteminin kalbi (0-100).
    - total_points: Read-heavy liderlik tablosu için denormalize sayaç.
      Kaynak gerçeği PointTransaction tablosudur; bu alan
      PointTransaction.save() sinyaliyle atomik güncellenir.
    - role: STUDENT / STAFF / ADMIN — view-level permission kontrolü için.
    """

    # username AbstractUser'dan miras alınır (profil URL'si için kullanılır).
    # Login identifier olarak email kullanıyoruz.
    email = models.EmailField(
        _("E-posta"),
        unique=True,
    )

    student_id = models.CharField(
        _("Öğrenci Numarası"),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text=_("Üniversite öğrenci numarası. Personel için boş bırakılabilir."),
    )

    department = models.CharField(
        _("Bölüm"),
        max_length=100,
        blank=True,
        help_text=_("Bölüm bazlı atık analizi ve ısı haritası için."),
    )

    trust_score = models.SmallIntegerField(
        _("Güven Puanı"),
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_(
            "Suistimal önleme skoru. "
            "Yeni kullanıcılar 50 ile başlar. "
            "Onaylı bildirimler artırır, reddedilen bildirimler düşürür."
        ),
    )

    total_points = models.PositiveIntegerField(
        _("Toplam Puan"),
        default=0,
        help_text=_(
            "Denormalize liderlik tablosu sayacı. "
            "Doğrudan güncelleme yapma — PointTransaction üzerinden yönetilir."
        ),
    )

    role = models.CharField(
        _("Rol"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
    )

    # Soft delete: Kullanıcı silinmez, pasif yapılır (KVKK uyumu).
    # AbstractUser.is_active alanı bu amaca hizmet eder; override gerekmez.

    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Güncellenme"), auto_now=True)

    # Django'ya login'de email kullanacağımızı söylüyoruz.
    USERNAME_FIELD = "email"
    # email, AbstractUser.REQUIRED_FIELDS'dan çıkarılmalı (zaten USERNAME_FIELD).
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = _("Kullanıcı")
        verbose_name_plural = _("Kullanıcılar")
        ordering = ["-created_at"]
        indexes = [
            # Rol + aktiflik filtresi: Admin panelinde en sık kullanılan sorgu.
            models.Index(fields=["role", "is_active"], name="idx_user_role_active"),
            # Öğrenci numarasına göre arama.
            models.Index(fields=["student_id"], name="idx_user_student_id"),
            # Liderlik tablosu: total_points DESC sıralaması.
            models.Index(fields=["-total_points"], name="idx_user_total_points"),
            # Bölüm bazlı analiz.
            models.Index(fields=["department"], name="idx_user_department"),
        ]

    def __str__(self) -> str:
        return f"{self.get_full_name()} <{self.email}>"

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    @property
    def is_staff_member(self) -> bool:
        """
        Django'nun built-in is_staff ile çakışmaması için is_staff_member kullanıyoruz.
        """
        return self.role == UserRole.STAFF

    def adjust_trust(self, delta: int, reason: str, related_object=None) -> None:
        """
        Trust score'u güvenli şekilde günceller ve log kaydı oluşturur.
        Bu metodu doğrudan çağır; trust_score alanını asla manuel güncelleme.

        Kullanım:
            user.adjust_trust(delta=+2, reason="REPORT_APPROVED", related_object=report)
        """
        from django.db.models import F

        # Atomic güncelleme: race condition'a karşı F() expression.
        User.objects.filter(pk=self.pk).update(
            trust_score=models.Case(
                models.When(trust_score__gt=100 - delta, then=100),
                models.When(trust_score__lt=0 - delta, then=0),
                default=F("trust_score") + delta,
                output_field=models.SmallIntegerField(),
            )
        )
        self.refresh_from_db(fields=["trust_score"])

        related_type = related_object.__class__.__name__ if related_object else ""
        related_id = getattr(related_object, "id", None)

        UserTrustLog.objects.create(
            user=self,
            delta=delta,
            score_after=self.trust_score,
            reason=reason,
            related_object_type=related_type,
            related_object_id=str(related_id) if related_id else None,
        )


class TrustChangeReason(models.TextChoices):
    """
    Trust log için enum. Yeni sebepler buraya eklenir.
    View katmanında string literal kullanmak yerine bu enum'u kullan.
    """

    REPORT_APPROVED = "REPORT_APPROVED", _("Bildirim Onaylandı")
    REPORT_REJECTED = "REPORT_REJECTED", _("Bildirim Reddedildi")
    VETTING_CORRECT = "VETTING_CORRECT", _("Denetim Oyu Doğru")
    VETTING_WRONG = "VETTING_WRONG", _("Denetim Oyu Yanlış")
    OBSERVATION_MODE = "OBSERVATION_MODE", _("Gözlem Modu Uygulandı")
    STREAK_BONUS = "STREAK_BONUS", _("30 Günlük Temiz Seri")
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", _("Manuel Düzeltme")
    DETECTIVE_CONFIRMED = "DETECTIVE_CONFIRMED", _("Dedektif Raporu Doğrulandı")


class UserTrustLog(models.Model):
    """
    Trust score her değiştiğinde neden değiştiğini kaydeder.

    Neden ayrı tablo?
    - Debug: "Bu kullanıcının skoru neden düştü?" sorusunu yanıtlar.
    - İtiraz: Kullanıcı haksız ceza aldığını düşünürse admin bu logu inceler.
    - Analiz: Hangi davranışlar trust'ı en çok etkiliyor?
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="trust_logs",
        verbose_name=_("Kullanıcı"),
    )
    delta = models.SmallIntegerField(
        _("Değişim"),
        help_text=_("Pozitif: artış, Negatif: düşüş. Örn: +2, -5"),
    )
    score_after = models.SmallIntegerField(
        _("Değişim Sonrası Skor"),
        help_text=_("Güncelleme sonrasındaki trust_score snapshot'ı."),
    )
    reason = models.CharField(
        _("Sebep"),
        max_length=50,
        choices=TrustChangeReason.choices,
    )
    related_object_type = models.CharField(
        _("İlişkili Nesne Türü"),
        max_length=50,
        blank=True,
        help_text=_("Hangi modelden tetiklendi. Örn: WasteReport, DetectiveReport"),
    )
    related_object_id = models.UUIDField(
        _("İlişkili Nesne ID"),
        null=True,
        blank=True,
        help_text=_("İlgili kaydın UUID'si. Audit trail için."),
    )
    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)

    class Meta:
        verbose_name = _("Güven Günlüğü")
        verbose_name_plural = _("Güven Günlükleri")
        ordering = ["-created_at"]
        indexes = [
            # Kullanıcının trust geçmişi — profil sayfası ve admin sorgularında kullanılır.
            models.Index(fields=["user", "-created_at"], name="idx_trustlog_user_date"),
            # Belirli sebep tiplerini analiz etmek için.
            models.Index(
                fields=["reason", "-created_at"], name="idx_trustlog_reason_date"
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.delta >= 0 else ""
        return f"{self.user.email} | {sign}{self.delta} | {self.reason}"
