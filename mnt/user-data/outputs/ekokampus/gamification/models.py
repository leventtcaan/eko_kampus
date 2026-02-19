# =============================================================================
# gamification/models.py
#
# Django App: gamification
# Bağımlılıklar: accounts
#
# Puan ve rozet sistemi.
# Önemli tasarım kararı: Puanlar PARA veya somut ödüle DÖNÜŞTÜRÜLMEZ.
# Sosyal görünürlük ve rozet yeterli motivasyon sağlar.
# Dönüştürme yapılırsa suistimal kaçınılmaz olur.
#
# total_points denormalize alanı:
# User.total_points doğrudan güncellenmez.
# PointTransaction.save() → post_save signal → User.total_points atomik güncellenir.
# Bu dosyada signal tanımı yapılmaz; accounts/signals.py'e konulmalı.
# =============================================================================

from __future__ import annotations

import uuid
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _


class BadgeType(models.TextChoices):
    MILESTONE = "MILESTONE", _("Kilometre Taşı")  # 50. bildirim gibi
    WEEKLY = "WEEKLY", _("Haftalık")  # Haftanın kahramanı
    SPECIAL = "SPECIAL", _("Özel")  # Etkinlik rozeti
    DETECTIVE = "DETECTIVE", _("Dedektif")  # Sorun tespit rozetleri
    VETTING = "VETTING", _("Denetçi")  # Kitle denetimi rozetleri
    BOUNTY = "BOUNTY", _("Bounty Avcısı")  # Görev tamamlama rozetleri


class Badge(models.Model):
    """
    Rozet tanım kataloğu.

    Sabit katalog — migration ile oluşturulur, admin panelinden yönetilir.
    Kullanıcılara atama: UserBadge tablosu üzerinden.

    code: Benzersiz string kimliği. View/signal kodlarında bu kullanılır.
          Örn: "FIRST_REPORT", "DETECTIVE_10", "WEEKLY_HERO"

    required_points (nullable):
        Dolu ise: Kullanıcı bu puana ulaştığında otomatik verilir.
        None ise: Celery task veya signal belirli bir eylemi tespit edince verir.

    icon_path:
        Media'daki SVG/PNG yolu. Frontend bu dosyayı render eder.
    """

    code = models.CharField(
        _("Rozet Kodu"),
        max_length=50,
        unique=True,
        help_text=_("Örn: FIRST_REPORT, DETECTIVE_10, WEEKLY_HERO"),
    )
    name = models.CharField(_("Rozet Adı"), max_length=100)
    description = models.TextField(_("Açıklama"), blank=True)
    icon_path = models.CharField(_("İkon Yolu"), max_length=300, blank=True)
    badge_type = models.CharField(
        _("Rozet Türü"),
        max_length=30,
        choices=BadgeType.choices,
        default=BadgeType.MILESTONE,
    )
    required_points = models.PositiveIntegerField(
        _("Gereken Puan"),
        null=True,
        blank=True,
        help_text=_(
            "Dolu ise: Bu puana ulaşınca otomatik verilir. Boş ise: Eylem bazlı."
        ),
    )
    is_active = models.BooleanField(_("Aktif"), default=True)

    class Meta:
        verbose_name = _("Rozet")
        verbose_name_plural = _("Rozetler")
        ordering = ["badge_type", "name"]
        indexes = [
            models.Index(
                fields=["badge_type", "is_active"], name="idx_badge_type_active"
            ),
            # Puan bazlı otomatik rozet kontrolü: "Bu puana karşılık rozet var mı?"
            models.Index(fields=["required_points"], name="idx_badge_points"),
        ]

    def __str__(self) -> str:
        return f"[{self.get_badge_type_display()}] {self.name} ({self.code})"


class UserBadge(models.Model):
    """
    Kullanıcı-Rozet ilişkisi.

    unique_together: Her rozet bir kullanıcıya bir kez verilir.

    related_object_type / related_object_id:
        Hangi eylem bu rozeti tetikledi?
        Audit ve "neden kazandın" açıklaması için.
        Örn: related_object_type="WasteReport", related_object_id=<uuid>
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="user_badges",
        verbose_name=_("Kullanıcı"),
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="user_badges",
        verbose_name=_("Rozet"),
    )
    awarded_at = models.DateTimeField(_("Kazanılma Zamanı"), auto_now_add=True)

    related_object_type = models.CharField(
        _("Tetikleyen Nesne Türü"),
        max_length=50,
        blank=True,
    )
    related_object_id = models.UUIDField(
        _("Tetikleyen Nesne ID"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Kullanıcı Rozeti")
        verbose_name_plural = _("Kullanıcı Rozetleri")
        ordering = ["-awarded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "badge"],
                name="unique_badge_per_user",
            )
        ]
        indexes = [
            # Profil sayfası: Kullanıcının tüm rozetleri.
            models.Index(
                fields=["user", "-awarded_at"], name="idx_userbadge_user_date"
            ),
            # "Bu rozet kaç kullanıcıda var?" — analitik.
            models.Index(
                fields=["badge", "-awarded_at"], name="idx_userbadge_badge_date"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} ← {self.badge.code} ({self.awarded_at:%Y-%m-%d})"


class TransactionType(models.TextChoices):
    REPORT_APPROVED = "REPORT_APPROVED", _("Bildirim Onaylandı")
    BOUNTY_CLAIMED = "BOUNTY_CLAIMED", _("Bounty Tamamlandı")
    VETTING_REWARD = "VETTING_REWARD", _("Denetim Ödülü")
    DETECTIVE_REWARD = "DETECTIVE_REWARD", _("Dedektif Ödülü")
    DELAYED_BONUS = "DELAYED_BONUS", _("Gecikmeli Puan Bonusu")
    PENALTY = "PENALTY", _("Ceza")
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT", _("Manuel Düzeltme")
    STREAK_BONUS = "STREAK_BONUS", _("Seri Bonusu")


class PointTransaction(models.Model):
    """
    Puan hareketinin tam kayıt defteri (ledger).

    Tasarım felsefesi:
    Bu tablo bir banka hesap özeti gibi davranır.
    User.total_points bakiyedir; bu tablo her işlemin detayıdır.
    Anlaşmazlık durumunda kaynak gerçeği burasıdır.

    amount:
        Pozitif → puan kazanıldı.
        Negatif → puan düşüldü (ileride "puan harcama" özelliği eklenirse).

    balance_after:
        İşlem sonrası User.total_points snapshot'ı.
        Neden saklıyoruz? Gelecekte bir transaction silinirse
        bakiye yeniden hesaplanabilir; hata ayıklama kolaylaşır.

    Signal entegrasyonu (accounts/signals.py'e yazılacak):
        @receiver(post_save, sender=PointTransaction)
        def update_user_total_points(sender, instance, created, **kwargs):
            if created:
                User.objects.filter(pk=instance.user_id).update(
                    total_points=F("total_points") + instance.amount
                )
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="point_transactions",
        verbose_name=_("Kullanıcı"),
    )
    amount = models.SmallIntegerField(
        _("Miktar"),
        help_text=_("Pozitif: kazanç. Negatif: düşüş."),
    )
    balance_after = models.IntegerField(
        _("İşlem Sonrası Bakiye"),
        help_text=_("User.total_points snapshot'ı. Audit ve hata ayıklama için."),
    )
    transaction_type = models.CharField(
        _("İşlem Türü"),
        max_length=30,
        choices=TransactionType.choices,
    )
    related_object_type = models.CharField(
        _("İlişkili Nesne Türü"),
        max_length=50,
        blank=True,
        help_text=_("Örn: WasteReport, Bounty, DetectiveReport"),
    )
    related_object_id = models.UUIDField(
        _("İlişkili Nesne ID"),
        null=True,
        blank=True,
    )
    note = models.CharField(
        _("Not"),
        max_length=200,
        blank=True,
        help_text=_("Manuel düzeltmeler için açıklama."),
    )
    created_at = models.DateTimeField(_("Zaman"), auto_now_add=True)

    class Meta:
        verbose_name = _("Puan İşlemi")
        verbose_name_plural = _("Puan İşlemleri")
        ordering = ["-created_at"]
        indexes = [
            # Kullanıcı puan geçmişi — profil ve Çevre Karnesi.
            models.Index(fields=["user", "-created_at"], name="idx_ptx_user_date"),
            # Tür bazlı analitik: "Bu ay kaç bounty ödülü verildi?"
            models.Index(
                fields=["transaction_type", "-created_at"], name="idx_ptx_type_date"
            ),
            # Belirli bir nesneye ait işlemler: "Bu raporun puanı ne zaman verildi?"
            models.Index(
                fields=["related_object_type", "related_object_id"],
                name="idx_ptx_related_object",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.amount >= 0 else ""
        return (
            f"{self.user.email} | {sign}{self.amount} | "
            f"{self.get_transaction_type_display()} | "
            f"Bakiye: {self.balance_after}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Yeni işlem kaydedilince User.total_points atomik güncellenir.

        Not: DetectiveVote.save()'de kullandığımız yaklaşımla tutarlı.
        Takım kararı: Signal mı, save override mı?
        Bu projede save() override tercih edildi — kayıt ve güncelleme
        birlikte, aynı transaction bloğunda kalır.

        Önemli: Sadece yeni kayıtlarda (is_new) güncelleme yap.
        Varolan bir transaction düzenlenmemeli; düzenleme gerekirse
        MANUAL_ADJUSTMENT ile yeni kayıt oluştur.
        """
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new:
            from accounts.models import User

            User.objects.filter(pk=self.user_id).update(
                total_points=F("total_points") + self.amount,
            )
