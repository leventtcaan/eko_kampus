# =============================================================================
# campus/models.py
#
# Django App: campus
# Bağımlılıklar: accounts
#
# Kampüsün fiziksel haritasını modeller: binalar ve çöp kutuları.
# Her çöp kutusu, fill_level alanıyla bir "sanal ikiz" (digital twin) taşır.
# Fiziksel sensör yok; doluluk hesabı WasteReport bildirimleriyle yapılır.
# =============================================================================

from __future__ import annotations

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class BuildingType(models.TextChoices):
    FACULTY = "FACULTY", _("Fakülte")
    DORM = "DORM", _("Yurt")
    CAFETERIA = "CAFETERIA", _("Kafeterya / Yemekhane")
    LIBRARY = "LIBRARY", _("Kütüphane")
    OUTDOOR = "OUTDOOR", _("Açık Alan")
    OTHER = "OTHER", _("Diğer")


class Building(models.Model):
    """
    Kampüs binası.

    Neden ayrı tablo?
    - Bina bazlı atık raporu: "Mühendislik binası bu ay kaç geri dönüşüm yaptı?"
    - GPS hata payı kararı: is_indoor=True ise geo-fence eşiği genişler.
    - Isı haritası katmanları: bina türüne göre renk kodlaması.
    """

    name = models.CharField(_("Bina Adı"), max_length=100)
    code = models.CharField(
        _("Bina Kodu"),
        max_length=20,
        unique=True,
        help_text=_("Kısa, benzersiz kod. Örn: MF-A, KUTUPHANE, B-BLOK"),
    )
    building_type = models.CharField(
        _("Bina Türü"),
        max_length=30,
        choices=BuildingType.choices,
        default=BuildingType.OTHER,
    )
    latitude = models.DecimalField(_("Enlem"), max_digits=9, decimal_places=6)
    longitude = models.DecimalField(_("Boylam"), max_digits=9, decimal_places=6)
    is_indoor = models.BooleanField(
        _("İç Mekan mı?"),
        default=True,
        help_text=_(
            "True ise bu binadaki kutular için geo-fence eşiği "
            "SystemSetting.GEO_FENCE_RADIUS_INDOOR_METERS kullanılır."
        ),
    )
    is_active = models.BooleanField(_("Aktif"), default=True)

    class Meta:
        verbose_name = _("Bina")
        verbose_name_plural = _("Binalar")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["building_type"], name="idx_building_type"),
            models.Index(fields=["is_active"], name="idx_building_active"),
            # Coğrafi yakınlık hesabı için koordinat indeksi.
            models.Index(fields=["latitude", "longitude"], name="idx_building_coords"),
        ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.name}"


class BinType(models.TextChoices):
    """
    Çöp kutusu türleri.
    Kullanıcı yanlış kategoride bildirim yaparsa Vision API uyarır.
    """

    GENERAL = "GENERAL", _("Genel Atık")
    RECYCLABLE = "RECYCLABLE", _("Geri Dönüşüm (Karma)")
    ORGANIC = "ORGANIC", _("Organik")
    GLASS = "GLASS", _("Cam")
    ELECTRONIC = "ELECTRONIC", _("Elektronik")
    PAPER = "PAPER", _("Kağıt")


class BinStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Aktif")
    MAINTENANCE = "MAINTENANCE", _("Bakımda")
    REMOVED = "REMOVED", _("Kaldırıldı")


class Bin(models.Model):
    """
    Çöp kutusu — sistemin fiziksel çekirdeği.

    id olarak UUID kullanılır çünkü bu UUID QR kod içeriğidir.
    Mobil uygulama QR'ı taradığında UUID'yi okur, API'ye gönderir.
    Integer PK kullansaydık QR'dan sıralı ID tahmini yapılabilirdi.

    fill_level:
        0.000 - 1.000 arası ondalık sayı.
        KULLANICI BU SAYIYI GİREMEZ.
        Sadece sistem hesaplar:
          - WasteReport onaylandığında artar (fill_delta kadar).
          - Temizlik personeli boşalttığında 0.000'a sıfırlanır.
          - Decay correction Celery task'ıyla periyodik uygulanır.

    last_emptied_at / last_report_at:
        Stagnation alert (hareketsizlik alarmı) için kritik.
        Celery Beat bu alanları periyodik olarak kontrol eder.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("QR kod içeriği. Mobil uygulama bu UUID'yi okur."),
    )
    code = models.CharField(
        _("Kutu Kodu"),
        max_length=20,
        unique=True,
        help_text=_("İnsan okunabilir kod. Örn: BIN-MF-A-01"),
    )
    building = models.ForeignKey(
        "campus.Building",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bins",
        verbose_name=_("Bina"),
        help_text=_("Dış mekan kutuları için boş bırakılabilir."),
    )
    location_description = models.CharField(
        _("Konum Açıklaması"),
        max_length=200,
        help_text=_(
            "Temizlik personeli için fiziksel yön tarifi. Örn: 'A Blok giriş kapısı sağı'"
        ),
    )
    latitude = models.DecimalField(_("Enlem"), max_digits=9, decimal_places=6)
    longitude = models.DecimalField(_("Boylam"), max_digits=9, decimal_places=6)

    bin_type = models.CharField(
        _("Kutu Türü"),
        max_length=30,
        choices=BinType.choices,
        default=BinType.GENERAL,
    )
    capacity_liters = models.PositiveSmallIntegerField(
        _("Kapasite (Litre)"),
        default=120,
        help_text=_(
            "Fiziksel hacim. fill_level kalibrasyonunda kullanılır. "
            "İleride kapasiteye göre fill_delta normalleştirilebilir."
        ),
    )

    # ------------------------------------------------------------------
    # Sanal Doluluk — Soft-sensing çekirdeği
    # ------------------------------------------------------------------
    fill_level = models.DecimalField(
        _("Doluluk"),
        max_digits=4,
        decimal_places=3,
        default=0.000,
        help_text=_(
            "0.000 = boş, 1.000 = taşıyor. "
            "Asla doğrudan güncelleme yapma; Bin.add_fill() metodunu kullan."
        ),
    )

    status = models.CharField(
        _("Durum"),
        max_length=20,
        choices=BinStatus.choices,
        default=BinStatus.ACTIVE,
    )
    last_emptied_at = models.DateTimeField(
        _("Son Boşaltma"),
        null=True,
        blank=True,
    )
    last_report_at = models.DateTimeField(
        _("Son Bildirim"),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("Aktif"), default=True)
    created_at = models.DateTimeField(_("Oluşturulma"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Güncellenme"), auto_now=True)

    class Meta:
        verbose_name = _("Çöp Kutusu")
        verbose_name_plural = _("Çöp Kutuları")
        ordering = ["code"]
        indexes = [
            # Aktif kutu listesi — harita ve lojistik paneli için en sık sorgu.
            models.Index(fields=["status", "is_active"], name="idx_bin_status_active"),
            # Kritik/uyarı eşiği filtrelemesi — Celery task ve dashboard için.
            models.Index(fields=["-fill_level"], name="idx_bin_fill_level"),
            # Coğrafi yakınlık — geo-fence kontrolü ve harita sorguları.
            models.Index(fields=["latitude", "longitude"], name="idx_bin_coords"),
            # Stagnation detection — "son boşaltmadan bu yana kaç saat geçti?"
            models.Index(fields=["last_emptied_at"], name="idx_bin_last_emptied"),
            models.Index(fields=["last_report_at"], name="idx_bin_last_report"),
            # Bina bazlı gruplama.
            models.Index(fields=["building"], name="idx_bin_building"),
        ]

    def __str__(self) -> str:
        return f"[{self.code}] {self.get_bin_type_display()} — Doluluk: {self.fill_level:.1%}"

    def add_fill(self, delta: float, triggered_by=None) -> None:
        """
        Doluluk seviyesini atomik olarak artırır ve BinStatusLog kaydı oluşturur.

        Neden F() expression?
        Eş zamanlı iki WasteReport aynı kutuya gelirse,
        Python'daki self.fill_level okuma-hesaplama-yazma döngüsü
        race condition yaratır. F() bu işlemi tek bir SQL UPDATE'e indirger.

        Kullanım:
            bin.add_fill(delta=0.05, triggered_by=report.user)
        """
        from django.db.models import F
        from django.utils import timezone
        import decimal

        delta_d = decimal.Decimal(str(delta))

        # fill_level 1.000'i asla aşamaz (cap mekanizması).
        Bin.objects.filter(pk=self.pk).update(
            fill_level=models.Case(
                models.When(
                    fill_level__gte=1 - delta_d,
                    then=decimal.Decimal("1.000"),
                ),
                default=F("fill_level") + delta_d,
                output_field=models.DecimalField(max_digits=4, decimal_places=3),
            ),
            last_report_at=timezone.now(),
        )
        self.refresh_from_db(fields=["fill_level", "last_report_at"])

        BinStatusLog.objects.create(
            bin=self,
            fill_level=self.fill_level,
            trigger=BinStatusLog.Trigger.REPORT,
            triggered_by=triggered_by,
        )

    def empty(self, triggered_by=None) -> None:
        """
        Kutuyu boşaltır. Sadece STAFF veya ADMIN rolündeki kullanıcılar
        çağırabilir (view katmanında kontrol edilmeli).
        """
        from django.utils import timezone

        Bin.objects.filter(pk=self.pk).update(
            fill_level=0.000,
            last_emptied_at=timezone.now(),
        )
        self.refresh_from_db(fields=["fill_level", "last_emptied_at"])

        BinStatusLog.objects.create(
            bin=self,
            fill_level=0.000,
            trigger=BinStatusLog.Trigger.EMPTIED,
            triggered_by=triggered_by,
        )

    @property
    def fill_status(self) -> str:
        """
        İnsan okunabilir eşik durumu.
        View ve template katmanında kullanılır; iş mantığı burada değil.
        """
        level = float(self.fill_level)
        if level >= 0.90:
            return "critical"
        if level >= 0.75:
            return "warning"
        if level >= 0.50:
            return "notice"
        return "normal"


class BinStatusLog(models.Model):
    """
    fill_level'in zaman serisi kaydı.

    Neden her değişimde log alıyoruz?
    - Tahminsel analitik: "Bu kutu Salı 12:00'da genellikle ne kadar dolu?"
    - Grafik: Doluluk eğrisi gösterimi.
    - Audit: "Bu kutu ne zaman kritik seviyeye geçti?"

    Bu tablo büyür! İleride (Faz 4+) created_at üzerine
    PostgreSQL table partitioning düşünülmeli.
    """

    class Trigger(models.TextChoices):
        REPORT = "REPORT", _("Kullanıcı Bildirimi")
        EMPTIED = "EMPTIED", _("Boşaltıldı")
        DECAY_CORRECTION = "DECAY_CORRECTION", _("Sıkışma Düzeltmesi")
        MANUAL = "MANUAL", _("Manuel Güncelleme")

    bin = models.ForeignKey(
        Bin,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("Çöp Kutusu"),
    )
    fill_level = models.DecimalField(
        _("Doluluk Anlık Değeri"),
        max_digits=4,
        decimal_places=3,
    )
    trigger = models.CharField(
        _("Tetikleyici"),
        max_length=30,
        choices=Trigger.choices,
    )
    triggered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bin_status_logs",
        verbose_name=_("Tetikleyen Kullanıcı"),
    )
    created_at = models.DateTimeField(_("Zaman"), auto_now_add=True)

    class Meta:
        verbose_name = _("Kutu Durum Günlüğü")
        verbose_name_plural = _("Kutu Durum Günlükleri")
        ordering = ["-created_at"]
        indexes = [
            # Kutu bazlı zaman serisi — grafik ve tahmin sorguları.
            models.Index(fields=["bin", "-created_at"], name="idx_binlog_bin_date"),
            # Tetikleyici türüne göre filtreleme — analitik için.
            models.Index(
                fields=["trigger", "-created_at"], name="idx_binlog_trigger_date"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.bin.code} | {self.fill_level:.1%} | {self.trigger} | {self.created_at:%Y-%m-%d %H:%M}"
