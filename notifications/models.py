# =============================================================================
# notifications/models.py
#
# Django App: notifications
# Bağımlılıklar: accounts
#
# Uygulama içi bildirim sistemi.
# Push notification gönderimi Celery task üzerinden yapılır (is_pushed takibi).
# HTMX: Her sayfa yüklemesinde okunmamış bildirim sayısı badge güncellenir.
# Mobil: REST API endpoint + push notification (Firebase/Expo).
# =============================================================================

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    # Lojistik bildirimleri (temizlik personeli + admin)
    BIN_WARNING = "BIN_WARNING", _("Kutu Uyarı Seviyesinde")
    BIN_CRITICAL = "BIN_CRITICAL", _("Kutu Kritik Seviyesinde")
    BIN_STAGNANT = "BIN_STAGNANT", _("Kutu Hareketsiz Kaldı")

    # Kullanıcı eylem bildirimleri
    REPORT_APPROVED = "REPORT_APPROVED", _("Bildirim Onaylandı")
    REPORT_REJECTED = "REPORT_REJECTED", _("Bildirim Reddedildi")

    # Kitle denetimi
    VETTING_REQUEST = "VETTING_REQUEST", _("Denetim Oyu İsteniyor")
    VETTING_RESOLVED = "VETTING_RESOLVED", _("Denetim Tamamlandı")

    # Bounty
    BOUNTY_AVAILABLE = "BOUNTY_AVAILABLE", _("Yakınında Yeni Görev")
    BOUNTY_AWARDED = "BOUNTY_AWARDED", _("Görev Ödülü Kazanıldı")
    BOUNTY_EXPIRING = "BOUNTY_EXPIRING", _("Görev Süresi Dolmak Üzere")

    # Dedektif
    DETECTIVE_CONFIRMED = "DETECTIVE_CONFIRMED", _("Sorun Raporu Doğrulandı")
    DETECTIVE_RESOLVED = "DETECTIVE_RESOLVED", _("Bildirdiğin Sorun Çözüldü")

    # Sistem
    TRUST_CHANGE = "TRUST_CHANGE", _("Güven Puanı Değişti")
    BADGE_AWARDED = "BADGE_AWARDED", _("Yeni Rozet Kazanıldı")
    WEEKLY_SUMMARY = "WEEKLY_SUMMARY", _("Haftalık Özet")
    AI_COACH_MESSAGE = "AI_COACH_MESSAGE", _("AI Koç Mesajı")


class Notification(models.Model):
    """
    Kullanıcıya iletilecek uygulama içi + push bildirim.

    data (JSONField):
        Push notification payload ve deep link için ek veri.
        Örn: {"bin_id": "uuid", "route": "/bins/uuid/"}
        Mobil uygulama bu data'ya göre ilgili ekrana yönlendirir.

    is_read / is_pushed:
        is_read:  Kullanıcı bildirimi uygulama içinde gördü.
        is_pushed: Firebase/Expo push notification gönderildi.
        İkisi bağımsız. Push gönderildi ama kullanıcı açmadıysa is_read=False kalır.

    related_object_type / related_object_id:
        "Hangi kayıtla ilgili bu bildirim?" sorusunu yanıtlar.
        HTMX: Bildirim tıklandığında ilgili sayfaya yönlendirir.
        Mobil: Deep link oluşturmak için kullanılır.

    Performans notu:
        Her sayfa yüklemesinde okunmamış bildirim sayısı sorgulanır.
        idx_notif_user_unread indeksi bu sorguyu hızlandırır.
        Alternatif: User.unread_notification_count denormalize sayacı
        (ileride gerekirse eklenebilir).
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Kullanıcı"),
    )
    notification_type = models.CharField(
        _("Bildirim Türü"),
        max_length=40,
        choices=NotificationType.choices,
    )
    title = models.CharField(_("Başlık"), max_length=200)
    body = models.TextField(_("İçerik"))
    data = models.JSONField(
        _("Ek Veri"),
        default=dict,
        blank=True,
        help_text=_("Deep link ve payload için. Örn: {'route': '/bins/uuid/'}"),
    )

    is_read = models.BooleanField(_("Okundu"), default=False)
    is_pushed = models.BooleanField(_("Push Gönderildi"), default=False)

    related_object_type = models.CharField(
        _("İlişkili Nesne Türü"),
        max_length=50,
        blank=True,
    )
    related_object_id = models.UUIDField(
        _("İlişkili Nesne ID"),
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)

    class Meta:
        verbose_name = _("Bildirim")
        verbose_name_plural = _("Bildirimler")
        ordering = ["-created_at"]
        indexes = [
            # Her sayfa yüklemesinde: "Bu kullanıcının okunmamış bildirimi var mı?"
            # Bu indeks olmadan her request full table scan yapar.
            models.Index(
                fields=["user", "is_read", "-created_at"],
                name="idx_notif_user_unread_date",
            ),
            # Push kuyruğu: "Gönderilmemiş push bildirimler neler?"
            models.Index(
                fields=["is_pushed", "-created_at"],
                name="idx_notif_push_pending",
            ),
            # Tür bazlı filtreleme.
            models.Index(
                fields=["notification_type", "-created_at"],
                name="idx_notif_type_date",
            ),
        ]

    def __str__(self) -> str:
        read_status = "✓" if self.is_read else "○"
        return f"[{read_status}] {self.user.email} | {self.title} | {self.created_at:%Y-%m-%d %H:%M}"
