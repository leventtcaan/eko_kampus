# =============================================================================
# bounties/models.py
#
# Django App: bounties
# Bağımlılıklar: accounts, campus, reports
#
# Kampüs Ödül Sistemi (Campus Bounty Board).
# Sistem veya admin tarafından oluşturulan görevler; öğrenciler tamamlar,
# ilk max_claimants kişi ödül kazanır.
#
# İki görev türü:
#   AUTO:   Celery Beat oluşturur. Örn: "Dolu kutu raporlama görevi"
#   MANUAL: Admin/Staff oluşturur. Örn: "Kütüphane bölgesinde farkındalık görevi"
#
# Puan enflasyonu önleme: max_claimants sınırı (default: 3).
# Race condition önleme: current_claimants F() expression ile atomik güncellenir.
# =============================================================================

from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class BountyType(models.TextChoices):
    AUTO = "AUTO", _("Sistem Otomatik")
    MANUAL = "MANUAL", _("Admin / Personel")


class BountyStatus(models.TextChoices):
    OPEN = "OPEN", _("Açık")
    CLOSED = "CLOSED", _("Kapalı")  # max_claimants doldu
    EXPIRED = "EXPIRED", _("Süresi Doldu")


class ClaimStatus(models.TextChoices):
    PENDING = "PENDING", _("Beklemede")
    AWARDED = "AWARDED", _("Ödüllendirildi")
    REJECTED = "REJECTED", _("Reddedildi")


class Bounty(models.Model):
    """
    Ödüllü kampüs görevi.

    target_bin (nullable):
        Kutu-spesifik görevler için. Örn: "BIN-LIB-03 kutusunu kontrol et."
        None ise bölgesel görev: target_latitude + target_longitude + target_radius.

    current_claimants (denormalize):
        BountyClaim sayısını her sorguda COUNT() ile hesaplamak yerine
        bu sayaç tutulur. Liderlik tablosu ve "kaç yer kaldı?" gösterimi için.
        Güncelleme: BountyClaim.save() → F("current_claimants") + 1 (atomik).

    required_waste_category (nullable):
        Sadece belirli atık kategorisi sayılsın. Örn: "Sadece cam bildirimleri geçerli."
        None ise tüm kategoriler kabul edilir.

    min_reports_required:
        Görevi tamamlamak için gereken bildirim sayısı.
        Default: 1 (tek bildirim yeterli).
        Örn: 5 → Kullanıcının o bölgeden 5 onaylı bildirim yapması gerekir.

    created_by (nullable):
        None → Sistem tarafından otomatik oluşturuldu.
        User → Admin veya Staff tarafından oluşturuldu.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(_("Başlık"), max_length=200)
    description = models.TextField(_("Açıklama"), blank=True)

    bounty_type = models.CharField(
        _("Görev Türü"),
        max_length=20,
        choices=BountyType.choices,
        default=BountyType.MANUAL,
    )

    # Hedef: Kutu-spesifik veya Bölgesel (biri dolu olmalı)
    target_bin = models.ForeignKey(
        "campus.Bin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bounties",
        verbose_name=_("Hedef Kutu"),
    )
    target_latitude = models.DecimalField(
        _("Hedef Enlem"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    target_longitude = models.DecimalField(
        _("Hedef Boylam"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    target_radius_meters = models.SmallIntegerField(
        _("Hedef Yarıçap (Metre)"),
        null=True,
        blank=True,
        help_text=_("Bölgesel görevlerde geçerli hedef alanı tanımlar."),
    )

    # Görev koşulları
    reward_points = models.PositiveSmallIntegerField(_("Ödül Puanı"))
    max_claimants = models.PositiveSmallIntegerField(
        _("Maksimum Kazanan"),
        default=3,
        help_text=_("İlk kaç kişi ödül alır? Puan enflasyonunu önler."),
    )
    current_claimants = models.PositiveSmallIntegerField(
        _("Mevcut Kazanan Sayısı"),
        default=0,
        help_text=_(
            "Denormalize sayaç. Manuel güncelleme yapma. "
            "BountyClaim oluşturulunca F() ile atomik artar."
        ),
    )
    required_waste_category = models.CharField(
        _("Gerekli Atık Kategorisi"),
        max_length=30,
        blank=True,
        help_text=_("Boş ise tüm kategoriler geçerli."),
    )
    min_reports_required = models.PositiveSmallIntegerField(
        _("Minimum Bildirim Sayısı"),
        default=1,
    )

    status = models.CharField(
        _("Durum"),
        max_length=20,
        choices=BountyStatus.choices,
        default=BountyStatus.OPEN,
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bounties",
        verbose_name=_("Oluşturan"),
        help_text=_("None = sistem otomatik oluşturdu."),
    )
    expires_at = models.DateTimeField(_("Bitiş Zamanı"))
    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)

    class Meta:
        verbose_name = _("Bounty Görevi")
        verbose_name_plural = _("Bounty Görevleri")
        ordering = ["-created_at"]
        indexes = [
            # Açık görev listesi — ana ekranda en sık sorgu.
            models.Index(
                fields=["status", "expires_at"], name="idx_bounty_status_expiry"
            ),
            # Türe göre filtreleme.
            models.Index(
                fields=["bounty_type", "status"], name="idx_bounty_type_status"
            ),
            # Kutu bazlı görev: "Bu kutunun aktif bounty'si var mı?"
            models.Index(fields=["target_bin", "status"], name="idx_bounty_bin_status"),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_bounty_type_display()}] {self.title} | "
            f"{self.current_claimants}/{self.max_claimants} | "
            f"{self.get_status_display()}"
        )

    @property
    def slots_remaining(self) -> int:
        """Kalan kazanma hakkı sayısı."""
        return max(0, self.max_claimants - self.current_claimants)

    @property
    def is_claimable(self) -> bool:
        """Yeni kazananlar için açık mı?"""
        return self.status == BountyStatus.OPEN and self.slots_remaining > 0


class BountyClaim(models.Model):
    """
    Kullanıcının bir bounty görevini tamamlaması.

    unique_together: Kullanıcı aynı görevi iki kez kazanamaz.

    qualifying_report (nullable):
        Hangi WasteReport bu görevi tamamladı?
        min_reports_required > 1 için bu alan son (tamamlayıcı) raporu gösterir.
        Bölgesel görevlerde None olabilir (birden fazla rapor var, tek link yok).

    Kazanma akışı (service katmanında):
        1. Kullanıcı bildirim yapar → WasteReport onaylanır.
        2. Service: Kullanıcının konumunda uygun OPEN bounty var mı? Kontrol.
        3. Varsa ve kullanıcı daha önce claim etmediyse → BountyClaim oluştur.
        4. Bounty.current_claimants atomik artır.
        5. Bounty doldu mu? (current ≥ max) → status = CLOSED.
        6. PointTransaction oluştur → User.total_points güncelle.
    """

    bounty = models.ForeignKey(
        Bounty,
        on_delete=models.CASCADE,
        related_name="claims",
        verbose_name=_("Görev"),
    )
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="bounty_claims",
        verbose_name=_("Kullanıcı"),
    )
    qualifying_report = models.ForeignKey(
        "reports.WasteReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bounty_claims",
        verbose_name=_("Tamamlayıcı Bildirim"),
    )
    points_awarded = models.PositiveSmallIntegerField(
        _("Verilen Puan"),
        default=0,
        help_text=_(
            "Bounty.reward_points'ten kopyalanır. Sonradan bounty değişirse etkilenmez."
        ),
    )
    status = models.CharField(
        _("Durum"),
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.PENDING,
    )
    claimed_at = models.DateTimeField(_("Talep Zamanı"), auto_now_add=True)
    awarded_at = models.DateTimeField(_("Ödül Zamanı"), null=True, blank=True)

    class Meta:
        verbose_name = _("Bounty Talebi")
        verbose_name_plural = _("Bounty Talepleri")
        ordering = ["-claimed_at"]
        constraints = [
            # Bir kullanıcı aynı görevi bir kez kazanabilir.
            models.UniqueConstraint(
                fields=["bounty", "user"],
                name="unique_bounty_claim_per_user",
            )
        ]
        indexes = [
            # "Bu görevin kaç talebi var ve durumu nedir?"
            models.Index(fields=["bounty", "status"], name="idx_claim_bounty_status"),
            # Kullanıcı geçmişi.
            models.Index(fields=["user", "-claimed_at"], name="idx_claim_user_date"),
            # Ödül bekleyen talepler — Celery task için.
            models.Index(
                fields=["status", "-claimed_at"], name="idx_claim_status_date"
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.user.email} → {self.bounty.title} | "
            f"{self.get_status_display()} | {self.points_awarded} puan"
        )
