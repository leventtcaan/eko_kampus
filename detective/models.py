# =============================================================================
# detective/models.py
#
# Django App: detective
# Bağımlılıklar: accounts, campus
#
# Çöp Dedektifi Modu — öğrenciler çevre sorunlarını tespit eder.
# Normal WasteReport: "Çöp attım."
# DetectiveReport:    "Sorun gördüm — yere atılmış atık / taşan kutu / yanlış ayrıştırma."
#
# Bu mod normal bildirim sisteminden ayrı tutuldu çünkü:
#   1. Farklı puan mekanizması (2× normal puan).
#   2. Farklı doğrulama akışı (onaylayan denetçiler, kutu değil sorun bildirir).
#   3. Temizlik personeli akışı farklı: sorun → çözüm → kapanış bildirimi.
#   4. Harita pinleri farklı renk ve ikon taşır.
# =============================================================================

from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProblemType(models.TextChoices):
    LITTERING = "LITTERING", _("Yere Atılmış Atık")
    OVERFLOWING = "OVERFLOWING", _("Taşmış / Açık Kutu")
    WRONG_SORT = "WRONG_SORT", _("Yanlış Ayrıştırma")
    DAMAGED_BIN = "DAMAGED_BIN", _("Hasarlı Kutu")
    OTHER = "OTHER", _("Diğer")


class DetectiveReportStatus(models.TextChoices):
    PENDING = "PENDING", _("Beklemede")
    CONFIRMED = "CONFIRMED", _("Doğrulandı")  # ≥3 kullanıcı onayı
    RESOLVED = "RESOLVED", _("Çözüldü")  # Personel kapattı
    REJECTED = "REJECTED", _("Reddedildi")  # Gerçek sorun değil


class DetectiveReport(models.Model):
    """
    Çevre sorunu tespiti.

    nearest_bin (nullable):
        Kullanıcının bildirdiği konuma en yakın çöp kutusu.
        Coğrafi hesaplama view katmanında yapılır.
        Haritada "bu sorun bu kutunun yakınında" bağlamı için kullanılır.

    confirmation_count (denormalize):
        DetectiveVote.filter(vote=CONFIRM).count() yerine bu sayaç.
        Neden? Haritada yüzlerce pin olduğunda her pin için COUNT() çekmek
        veritabanını mahveder. Bu sayaç pin rengi/büyüklüğü için hızlı referans.
        Güncelleme: DetectiveVote.save() sinyaliyle atomik artış.

    resolved_by / resolved_at:
        Temizlik personeli sorunu çözünce doldurur.
        Uygulama bu kapanışı bildiren kişiye "Bildirdiğin sorun çözüldü!" push gönderir.
        Bu davranış pekiştirici döngüsü (behavioral loop closure) kullanım oranını artırır.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reporter = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detective_reports",
        verbose_name=_("Bildiren"),
    )
    problem_type = models.CharField(
        _("Sorun Türü"),
        max_length=30,
        choices=ProblemType.choices,
    )

    # Sorunun tam koordinatı — kutu koordinatıyla aynı olmayabilir.
    latitude = models.DecimalField(_("Enlem"), max_digits=9, decimal_places=6)
    longitude = models.DecimalField(_("Boylam"), max_digits=9, decimal_places=6)

    nearest_bin = models.ForeignKey(
        "campus.Bin",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detective_reports",
        verbose_name=_("En Yakın Kutu"),
        help_text=_("Coğrafi hesaplamayla otomatik doldurulur."),
    )

    # Fotoğraf kanıtı
    image_path = models.CharField(
        _("Fotoğraf Yolu"),
        max_length=500,
        blank=True,
    )
    image_hash = models.CharField(
        _("Fotoğraf Hash"),
        max_length=64,
        blank=True,
        db_index=True,
    )

    # Vision API sonuçları
    ai_problem_detected = models.BooleanField(
        _("AI: Sorun Tespit Edildi mi?"),
        null=True,
        blank=True,
    )
    ai_problem_type_suggestion = models.CharField(
        _("AI: Önerilen Sorun Türü"),
        max_length=30,
        blank=True,
    )
    ai_confidence_score = models.DecimalField(
        _("AI: Güven Skoru"),
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
    )
    ai_raw_response = models.JSONField(
        _("AI: Ham Yanıt"),
        null=True,
        blank=True,
    )

    # Kitle doğrulama
    confirmation_count = models.SmallIntegerField(
        _("Doğrulama Sayısı"),
        default=0,
        help_text=_(
            "Denormalize sayaç. Harita pin boyutu ve rengi için. "
            "DetectiveVote.save() sinyaliyle güncellenir."
        ),
    )

    status = models.CharField(
        _("Durum"),
        max_length=20,
        choices=DetectiveReportStatus.choices,
        default=DetectiveReportStatus.PENDING,
    )
    points_awarded = models.SmallIntegerField(_("Verilen Puan"), default=0)

    # Çözüm bilgisi
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_detective_reports",
        verbose_name=_("Çözen Personel"),
    )
    resolved_at = models.DateTimeField(_("Çözülme Zamanı"), null=True, blank=True)

    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)

    class Meta:
        verbose_name = _("Dedektif Raporu")
        verbose_name_plural = _("Dedektif Raporları")
        ordering = ["-created_at"]
        indexes = [
            # Durum + zaman — admin ve temizlik paneli için.
            models.Index(
                fields=["status", "-created_at"], name="idx_detrep_status_date"
            ),
            # Harita sorgusu: Belirli koordinat aralığındaki aktif sorunlar.
            models.Index(fields=["latitude", "longitude"], name="idx_detrep_coords"),
            # En yakın kutu bazlı — "Bu kutunun açık sorunları neler?"
            models.Index(
                fields=["nearest_bin", "status"], name="idx_detrep_bin_status"
            ),
            # Bildiren kullanıcı geçmişi.
            models.Index(
                fields=["reporter", "-created_at"], name="idx_detrep_reporter"
            ),
            # Kapanış sorgusal: "Son 7 günde çözülen sorunlar?"
            models.Index(fields=["resolved_at"], name="idx_detrep_resolved"),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_problem_type_display()}] "
            f"{self.get_status_display()} | "
            f"Doğrulama: {self.confirmation_count}"
        )


class DetectiveVote(models.Model):
    """
    Diğer kullanıcıların DetectiveReport'u doğrulaması.

    Mantık: 3 doğrulama → rapor CONFIRMED statüsüne geçer.
    CONFIRMED raporlar haritada daha belirgin görünür ve personele öncelikli iletilir.

    WasteReport.VettingVote'tan farkı:
    - VettingVote: "Bu bildirimi sahte mi?" (suistimal kontrolü)
    - DetectiveVote: "Bu sorunu gerçekten gördüm, doğruluyorum." (meydan okuma değil, teyit)
    """

    class Vote(models.TextChoices):
        CONFIRM = "CONFIRM", _("Doğruluyorum")
        REJECT = "REJECT", _("Göremedim / Yanlış")

    detective_report = models.ForeignKey(
        DetectiveReport,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name=_("Dedektif Raporu"),
    )
    voter = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="detective_votes_cast",
        verbose_name=_("Oy Veren"),
    )
    vote = models.CharField(
        _("Oy"),
        max_length=10,
        choices=Vote.choices,
    )
    voter_distance_meters = models.SmallIntegerField(
        _("Oy Veren Kişinin Mesafesi (Metre)"),
        default=0,
        help_text=_(
            "Oy verenin sorun noktasına yakınlığı. Ağırlık hesabında kullanılır."
        ),
    )
    created_at = models.DateTimeField(_("Oy Zamanı"), auto_now_add=True)

    class Meta:
        verbose_name = _("Dedektif Oyu")
        verbose_name_plural = _("Dedektif Oyları")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["detective_report", "voter"],
                name="unique_detective_vote_per_user",
            )
        ]
        indexes = [
            # Oy sayımı.
            models.Index(
                fields=["detective_report", "vote"],
                name="idx_detvote_report_vote",
            ),
            # Kullanıcı oy geçmişi.
            models.Index(
                fields=["voter", "-created_at"],
                name="idx_detvote_voter_date",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.voter.email} → {self.detective_report_id} | "
            f"{self.get_vote_display()}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Oy kaydedilince DetectiveReport.confirmation_count atomik güncellenir.

        Not: Bu mantık Django signal (post_save) ile de yapılabilir.
        Burada save() override tercih edildi çünkü:
        - Sinyal kayıt sırası bazen belirsizleşir.
        - Bu güncelleme bu modelin doğrudan sorumluluğu.
        Takım bu kararı tutarlı uygulasın (ya hep signal, ya hep save override).
        """
        from django.db.models import F

        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new and self.vote == self.Vote.CONFIRM:
            DetectiveReport.objects.filter(pk=self.detective_report_id).update(
                confirmation_count=F("confirmation_count") + 1
            )
