# =============================================================================
# reports/models.py
#
# Django App: reports
# Bağımlılıklar: accounts, campus
#
# Sistemin kalbi. Kullanıcının "çöp attım" eylemini temsil eden WasteReport
# ve buna bağlı fotoğraf kanıtı + kitle denetimi tablolarını içerir.
#
# Kritik iş kuralları (view/service katmanında uygulanır, burada not olarak):
#   1. fill_delta hesabı: base_volume × decay_correction — view'da yapılır.
#   2. Frekans kilidi: Aynı kullanıcı + kutu ikilisi 15 dk içinde tekrar rapor edemez.
#   3. Geo-fence: Kullanıcı koordinatı, kutu koordinatına max N metre yakın olmalı.
#   4. Time-spoofing: client_timestamp ile created_at farkı 24 saati aşarsa red.
#   5. Suspicion score: Birden fazla faktörden hesaplanır, view'da set edilir.
# =============================================================================

from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class WasteCategory(models.TextChoices):
    """
    Atık kategorileri ve base_volume değerleri.
    base_volume: Soft-sensing doluluk artış katsayısı.
    Bu değerler SystemSetting üzerinden de override edilebilir (ileride).
    """

    PAPER = "PAPER", _("Kağıt / Karton")  # base_volume: 0.04
    PLASTIC = "PLASTIC", _("Plastik")  # base_volume: 0.05
    GLASS = "GLASS", _("Cam")  # base_volume: 0.03
    ORGANIC = "ORGANIC", _("Organik")  # base_volume: 0.06
    ELECTRONIC = "ELECTRONIC", _("Elektronik")  # base_volume: 0.08
    GENERAL = "GENERAL", _("Genel / Karışık")  # base_volume: 0.05
    SMALL = "SMALL", _("Küçük (İzmarit vb.)")  # base_volume: 0.01


# Kategori → base_volume eşleşmesi.
# View katmanında fill_delta hesabında kullanılır.
CATEGORY_BASE_VOLUME: dict[str, float] = {
    WasteCategory.PAPER: 0.04,
    WasteCategory.PLASTIC: 0.05,
    WasteCategory.GLASS: 0.03,
    WasteCategory.ORGANIC: 0.06,
    WasteCategory.ELECTRONIC: 0.08,
    WasteCategory.GENERAL: 0.05,
    WasteCategory.SMALL: 0.01,
}


class VerificationMethod(models.TextChoices):
    PHOTO = "PHOTO", _("Fotoğraf")
    QR = "QR", _("QR Kod")
    BOTH = "BOTH", _("Fotoğraf + QR")


class ReportStatus(models.TextChoices):
    PENDING = "PENDING", _("Beklemede")
    APPROVED = "APPROVED", _("Onaylandı")
    REJECTED = "REJECTED", _("Reddedildi")
    UNDER_VETTING = "UNDER_VETTING", _("Kitle Denetiminde")


class WasteReport(models.Model):
    """
    Bir kullanıcının "çöp attım" bildirimi.

    UUID PK: GET /api/reports/1/ yerine GET /api/reports/a3f7.../
    Sıralı integer ID kullanıcıların başkasının raporlarını tahmin etmesini engeller.

    client_timestamp vs created_at:
        client_timestamp: Kullanıcının telefonu "gönder"e bastığı an.
                          Offline-first senaryo: bağlantı olmadan depolanır,
                          bağlantı gelince gönderilir.
        created_at:       Sunucunun paketi aldığı an.
        Fark 24 saati aşarsa → Time-spoofing koruması → otomatik red.

    fill_delta:
        Bu rapor onaylandığında kutuya eklenecek doluluk miktarı.
        Hesabı view'da yapılır, buraya saklanır.
        Reddedilen raporlarda fill_delta uygulanmaz.

    suspicion_score:
        Birden çok faktörden hesaplanan risk puanı (0-100).
        ≥ 40 → Kitle denetimine gönder.
        ≥ 100 → Otomatik red.
        Hesaplama view/service katmanında yapılır; model sadece saklar.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="waste_reports",
        verbose_name=_("Kullanıcı"),
        help_text=_("SET_NULL: Kullanıcı silinse bile rapor istatistiklerde kalır."),
    )
    bin = models.ForeignKey(
        "campus.Bin",
        on_delete=models.CASCADE,
        related_name="waste_reports",
        verbose_name=_("Çöp Kutusu"),
    )

    waste_category = models.CharField(
        _("Atık Kategorisi"),
        max_length=30,
        choices=WasteCategory.choices,
    )
    verification_method = models.CharField(
        _("Doğrulama Yöntemi"),
        max_length=20,
        choices=VerificationMethod.choices,
    )

    # Kullanıcının bildirimi başlattığı andaki GPS koordinatı.
    latitude = models.DecimalField(_("Enlem"), max_digits=9, decimal_places=6)
    longitude = models.DecimalField(_("Boylam"), max_digits=9, decimal_places=6)

    # Hesaplanmış değerler — view'da doldurulur.
    geo_distance_meters = models.SmallIntegerField(
        _("Kutuya Mesafe (Metre)"),
        default=0,
        help_text=_("Kullanıcı koordinatı ile kutu koordinatı arasındaki mesafe."),
    )
    fill_delta = models.DecimalField(
        _("Doluluk Artışı"),
        max_digits=4,
        decimal_places=3,
        default=0.000,
        help_text=_(
            "Bu rapor onaylandığında kutunun fill_level değerine eklenecek miktar. "
            "Formül: base_volume × decay_correction"
        ),
    )
    suspicion_score = models.SmallIntegerField(
        _("Şüphe Skoru"),
        default=0,
        help_text=_(
            "0-100 arası. ≥40 kitle denetimine gönderir, ≥100 otomatik reddeder."
        ),
    )

    status = models.CharField(
        _("Durum"),
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )
    points_awarded = models.SmallIntegerField(
        _("Verilen Puan"),
        default=0,
        help_text=_("Onay sonrası verilen puan. Gecikmeli puanlama için 0 olabilir."),
    )

    # Zaman damgaları
    client_timestamp = models.DateTimeField(
        _("İstemci Zaman Damgası"),
        help_text=_(
            "Kullanıcı cihazının bildirimi BAŞLATTIĞI an. "
            "Offline sync için: sunucu bu değeri iş mantığında baz alır. "
            "Güvenlik: Sunucu zamanından 24 saat farklıysa bildirim reddedilir."
        ),
    )
    created_at = models.DateTimeField(
        _("Sunucu Alım Zamanı"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Atık Bildirimi")
        verbose_name_plural = _("Atık Bildirimleri")
        ordering = ["-created_at"]
        indexes = [
            # Kutu bazlı tarihsel sorgu — tahminsel analitik için.
            models.Index(fields=["bin", "-created_at"], name="idx_report_bin_date"),
            # Kullanıcı geçmişi — profil sayfası.
            models.Index(fields=["user", "-created_at"], name="idx_report_user_date"),
            # Frekans kilidi kontrolü: "Bu kullanıcı + kutu son 15 dk içinde rapor etti mi?"
            models.Index(
                fields=["user", "bin", "-client_timestamp"], name="idx_report_ratelock"
            ),
            # Durum bazlı filtreleme — admin paneli ve Celery task.
            models.Index(
                fields=["status", "-created_at"], name="idx_report_status_date"
            ),
            # Yüksek şüpheli raporları bul.
            models.Index(fields=["-suspicion_score"], name="idx_report_suspicion"),
            # Anomali dedektörü: Saatlik bildirim sayısı hesabı.
            models.Index(
                fields=["bin", "status", "-client_timestamp"], name="idx_report_anomaly"
            ),
        ]
        # Frekans kilidi için veritabanı seviyesi kısıt YOK;
        # bu kontrol view/service katmanında yapılır.
        # Neden? Kilidi 15 dakikalık bir zaman penceresi tanımlar;
        # bu tip "zaman bazlı unique" kısıtı SQL constraint ile ifade edilemez.

    def __str__(self) -> str:
        return (
            f"{getattr(self.user, 'email', 'Anonim')} | "
            f"{self.get_waste_category_display()} | "
            f"{self.bin.code} | "
            f"{self.get_status_display()}"
        )

    @property
    def is_high_suspicion(self) -> bool:
        return self.suspicion_score >= 40

    @property
    def should_auto_reject(self) -> bool:
        return self.suspicion_score >= 100


class PhotoEvidence(models.Model):
    """
    Fotoğraf kanıtı ve OpenAI Vision API analiz sonuçları.

    Neden WasteReport'tan ayrı tablo?
    1. QR-only bildirimler fotoğraf taşımaz. Her rapora nullable fotoğraf alanı
       eklemek şemayı kirletir; OneToOne ilişki daha temiz.
    2. Vision analizi asenkron (Celery task). Rapor kaydedilir,
       fotoğraf analizi sonra gelir. ai_analyzed_at None → analiz bekleniyor.
    3. Fotoğraf 30 gün sonra silinir (KVKK). Rapor verisi kalır.
       Silme işlemi: image_path temizlenir, diğer alanlar kalır.

    image_hash:
        SHA256 fingerprint. Aynı hash + aynı kullanıcı + 7 gün içinde → otomatik red.
        Aynı hash + farklı kullanıcı → suspicion_score +15.
    """

    report = models.OneToOneField(
        WasteReport,
        on_delete=models.CASCADE,
        related_name="photo_evidence",
        verbose_name=_("Atık Bildirimi"),
    )
    image_path = models.CharField(
        _("Fotoğraf Yolu"),
        max_length=500,
        help_text=_("Media storage path. Örn: reports/2024/01/uuid.jpg"),
    )
    image_hash = models.CharField(
        _("Fotoğraf Hash (SHA256)"),
        max_length=64,
        db_index=True,
        help_text=_("Tekrar kullanım tespiti için SHA256 parmak izi."),
    )

    # Vision API sonuçları — Celery task doldurur, başlangıçta None.
    ai_bin_detected = models.BooleanField(
        _("AI: Kutu Tespit Edildi mi?"),
        null=True,
        blank=True,
    )
    ai_waste_detected = models.BooleanField(
        _("AI: Atık Tespit Edildi mi?"),
        null=True,
        blank=True,
    )
    ai_category_suggestion = models.CharField(
        _("AI: Önerilen Kategori"),
        max_length=30,
        blank=True,
        help_text=_(
            "Vision API'nin önerdiği atık kategorisi. Kullanıcı seçimiyle karşılaştırılır."
        ),
    )
    ai_confidence_score = models.DecimalField(
        _("AI: Güven Skoru"),
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=_(
            "0.000 - 1.000 arası. 0.500 altı düşük güven → suspicion_score artar."
        ),
    )
    ai_is_stock_photo = models.BooleanField(
        _("AI: Stok Fotoğraf mı?"),
        null=True,
        blank=True,
    )
    ai_raw_response = models.JSONField(
        _("AI: Ham Yanıt"),
        null=True,
        blank=True,
        help_text=_("OpenAI API'nin tam JSON yanıtı. Debug ve audit için saklanır."),
    )
    ai_analyzed_at = models.DateTimeField(
        _("AI Analiz Zamanı"),
        null=True,
        blank=True,
        help_text=_("None ise analiz henüz yapılmamış (Celery kuyruğunda)."),
    )
    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)

    class Meta:
        verbose_name = _("Fotoğraf Kanıtı")
        verbose_name_plural = _("Fotoğraf Kanıtları")
        indexes = [
            # Tekrar kullanım tespiti: "Bu hash bugün daha önce görüldü mü?"
            models.Index(
                fields=["image_hash", "-created_at"], name="idx_photo_hash_date"
            ),
            # Analiz kuyruğu: "Henüz analiz edilmemiş fotoğraflar neler?"
            models.Index(fields=["ai_analyzed_at"], name="idx_photo_analyzed"),
        ]

    def __str__(self) -> str:
        status = "Analiz edildi" if self.ai_analyzed_at else "Analiz bekleniyor"
        return f"Fotoğraf [{self.report_id}] — {status}"


class VettingVote(models.Model):
    """
    Kitle denetim oyu.

    Bir WasteReport, suspicion_score ≥ 40 olduğunda UNDER_VETTING statüsüne geçer.
    Yakın mesafedeki kullanıcılara bildirim gönderilir.
    Onlar APPROVE veya REJECT oyu verir.

    Karar algoritması (view/service katmanında):
        Toplam oy ≥ VETTING_MIN_VOTES (3) ise:
            APPROVE oy oranı ≥ VETTING_APPROVE_THRESHOLD (0.60) → raporu onayla
            REJECT  oy oranı > (1 - threshold) → raporu reddet
        30 dakika içinde yeterli oy gelmezse → ön ödeme kalıcılaştır.

    voter_trust_at_vote:
        Oy anındaki trust score snapshot'ı. Düşük trust'lı denetçilerin oyları
        %50 ağırlık taşır. Ağırlıklı oy hesabı service katmanında yapılır.
        Bu alan sayesinde "oy sonrası trust düşüşü" geçmişe etkimez.

    voter_distance_meters:
        Denetçinin oy verdiği andaki konumundan hesaplanan mesafe.
        Aynı yurt/bölümden gelen oyların ağırlığını normalize etmek için kullanılır.
    """

    class Vote(models.TextChoices):
        APPROVE = "APPROVE", _("Onayla")
        REJECT = "REJECT", _("Reddet")

    report = models.ForeignKey(
        WasteReport,
        on_delete=models.CASCADE,
        related_name="vetting_votes",
        verbose_name=_("Bildirim"),
    )
    voter = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="vetting_votes_cast",
        verbose_name=_("Denetçi"),
    )
    vote = models.CharField(
        _("Oy"),
        max_length=10,
        choices=Vote.choices,
    )
    voter_trust_at_vote = models.SmallIntegerField(
        _("Denetçinin Oy Anındaki Trust Skoru"),
        help_text=_("Snapshot. Sonradan trust değişirse bu oyu etkilemez."),
    )
    voter_distance_meters = models.SmallIntegerField(
        _("Denetçinin Kutuya Uzaklığı (Metre)"),
        default=0,
    )
    created_at = models.DateTimeField(_("Oy Zamanı"), auto_now_add=True)

    class Meta:
        verbose_name = _("Denetim Oyu")
        verbose_name_plural = _("Denetim Oyları")
        ordering = ["created_at"]
        # Aynı kullanıcı aynı rapora iki kez oy veremez.
        constraints = [
            models.UniqueConstraint(
                fields=["report", "voter"],
                name="unique_vetting_vote_per_user",
            )
        ]
        indexes = [
            # Oy sayımı: "Bu rapor için kaç onay/ret var?"
            models.Index(fields=["report", "vote"], name="idx_vetting_report_vote"),
            # Kullanıcı denetim geçmişi.
            models.Index(
                fields=["voter", "-created_at"], name="idx_vetting_voter_date"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.voter.email} → {self.report_id} | {self.get_vote_display()}"
