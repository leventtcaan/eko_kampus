# =============================================================================
# config/models.py
#
# Django App: config
# Bağımlılıklar: django.core.cache (Redis)
#
# Sistem Ayarları — Hard-coded sıfır toleransı.
# Tüm eşik değerleri, yarıçaplar, oranlar bu tablodan okunur.
# Admin panelinden güncellenir; uygulama restart gerekmez.
# Redis cache ile 5 dakika TTL — her istekte DB sorgusu yapmaz.
#
# Başlangıç verisi (seed): data/system_settings.json fixture ile yüklenir.
# =============================================================================

from __future__ import annotations

from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy as _


class ValueType(models.TextChoices):
    """
    Tüm değerler DB'de string. Bu field uygulamanın parse etmesini sağlar.
    SystemSetting.get() metodu bunu otomatik yapar.
    """

    INT = "INT", _("Tam Sayı")
    FLOAT = "FLOAT", _("Ondalık Sayı")
    BOOL = "BOOL", _("Mantıksal (true/false)")
    STRING = "STRING", _("Metin")


class SystemSetting(models.Model):
    """
    Uygulama genelinde geçerli yapılandırma parametreleri.

    Felsefe:
        Bu projede hiçbir sayı Python koduna gömülmez.
        "GEO_FENCE_RADIUS_METERS = 30" yazmak yasak.
        Doğrusu: SystemSetting.get("GEO_FENCE_RADIUS_METERS", default=30)

    Cache mekanizması:
        Her get() çağrısı önce Redis'e bakar.
        Cache miss → DB sorgusu → Redis'e 300 saniye (5 dk) yaz.
        Admin panelinden güncelleme → save() signal cache'i invalidate eder.

    Örnek kullanım (view/service katmanında):
        radius = SystemSetting.get("GEO_FENCE_RADIUS_METERS", default=30)
        threshold = SystemSetting.get("FILL_CRITICAL_THRESHOLD", default=0.90)
        enabled = SystemSetting.get("BOUNTY_SYSTEM_ENABLED", default=True)
    """

    CACHE_PREFIX = "syssetting:"
    CACHE_TTL = 300  # saniye (5 dakika)

    key = models.CharField(
        _("Anahtar"),
        max_length=100,
        unique=True,
        help_text=_("SCREAMING_SNAKE_CASE. Örn: GEO_FENCE_RADIUS_METERS"),
    )
    value = models.CharField(
        _("Değer"),
        max_length=500,
        help_text=_("Her zaman string. value_type alanına göre parse edilir."),
    )
    value_type = models.CharField(
        _("Değer Tipi"),
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.STRING,
    )
    description = models.TextField(
        _("Açıklama"),
        help_text=_("Bu ayar ne işe yarar? Hangi modülü etkiler?"),
    )
    updated_at = models.DateTimeField(_("Son Güncelleme"), auto_now=True)

    class Meta:
        verbose_name = _("Sistem Ayarı")
        verbose_name_plural = _("Sistem Ayarları")
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} = {self.value} ({self.get_value_type_display()})"

    def save(self, *args, **kwargs) -> None:
        """
        Kayıt güncellenince ilgili cache anahtarını sil.
        Bir sonraki get() çağrısı DB'den taze değeri okuyacak.
        """
        cache.delete(f"{self.CACHE_PREFIX}{self.key}")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        cache.delete(f"{self.CACHE_PREFIX}{self.key}")
        return super().delete(*args, **kwargs)

    # ------------------------------------------------------------------
    # Cache-aware getter — Tek erişim noktası
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, key: str, default=None):
        """
        Sistem ayarını döndürür. Cache'den okur, yoksa DB'den çeker ve cache'e yazar.

        Kullanım:
            radius = SystemSetting.get("GEO_FENCE_RADIUS_METERS", default=30)

        Tip dönüşümü value_type'a göre otomatik yapılır:
            INT    → int
            FLOAT  → float
            BOOL   → bool ("true"/"1"/"yes" → True, diğeri → False)
            STRING → str

        Anahtar bulunamazsa default döner.
        """
        cache_key = f"{cls.CACHE_PREFIX}{key}"
        cached = cache.get(cache_key)

        if cached is not None:
            return cached

        try:
            setting = cls.objects.get(key=key)
            parsed = cls._parse(setting.value, setting.value_type)
            cache.set(cache_key, parsed, cls.CACHE_TTL)
            return parsed
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_many(cls, keys: list[str]) -> dict:
        """
        Birden fazla ayarı tek sorguda çeker.
        View başlangıcında birden fazla ayar gerekiyorsa performanslıdır.

        Kullanım:
            settings = SystemSetting.get_many([
                "GEO_FENCE_RADIUS_METERS",
                "FILL_CRITICAL_THRESHOLD",
                "VETTING_MIN_VOTES",
            ])
            radius    = settings.get("GEO_FENCE_RADIUS_METERS", 30)
            threshold = settings.get("FILL_CRITICAL_THRESHOLD", 0.90)
        """
        result = {}
        cache_keys = {k: f"{cls.CACHE_PREFIX}{k}" for k in keys}
        cached = cache.get_many(list(cache_keys.values()))

        missing_keys = [k for k, ck in cache_keys.items() if ck not in cached]

        if missing_keys:
            db_settings = cls.objects.filter(key__in=missing_keys)
            to_cache = {}

            for setting in db_settings:
                parsed = cls._parse(setting.value, setting.value_type)
                to_cache[cache_keys[setting.key]] = parsed
                result[setting.key] = parsed

            if to_cache:
                cache.set_many(to_cache, cls.CACHE_TTL)

        for k, ck in cache_keys.items():
            if ck in cached:
                result[k] = cached[ck]

        return result

    @staticmethod
    def _parse(value: str, value_type: str):
        """Ham string değeri doğru Python tipine dönüştürür."""
        if value_type == ValueType.INT:
            return int(value)
        if value_type == ValueType.FLOAT:
            return float(value)
        if value_type == ValueType.BOOL:
            return value.strip().lower() in ("true", "1", "yes", "evet")
        return value  # STRING


# ------------------------------------------------------------------
# Başlangıç veri sabitleri
# Bu dict, management command veya fixture ile DB'ye yüklenir.
# Kod içinde doğrudan KULLANILMAZ; sadece referans ve seed için.
# ------------------------------------------------------------------

INITIAL_SETTINGS: list[dict] = [
    # Coğrafi doğrulama
    {
        "key": "GEO_FENCE_RADIUS_METERS",
        "value": "30",
        "value_type": "INT",
        "description": "Standart geo-fence yarıçapı (metre). Kullanıcı bu mesafe dışından bildirim yapamaz.",
    },
    {
        "key": "GEO_FENCE_RADIUS_INDOOR_METERS",
        "value": "50",
        "value_type": "INT",
        "description": "İç mekan kutuları için genişletilmiş geo-fence yarıçapı.",
    },
    # Kitle denetimi
    {
        "key": "VETTING_RADIUS_METERS",
        "value": "200",
        "value_type": "INT",
        "description": "Kitle denetim daveti yarıçapı. Onaylanırsa dinamik genişletilebilir.",
    },
    {
        "key": "VETTING_MIN_VOTES",
        "value": "3",
        "value_type": "INT",
        "description": "Karar için gereken minimum oy sayısı.",
    },
    {
        "key": "VETTING_APPROVE_THRESHOLD",
        "value": "0.6",
        "value_type": "FLOAT",
        "description": "Onay kararı için gereken oy oranı (0.0-1.0).",
    },
    {
        "key": "VETTING_TIMEOUT_MINUTES",
        "value": "30",
        "value_type": "INT",
        "description": "Yeterli oy gelmezse bekleme süresi (dakika).",
    },
    # Frekans kilidi
    {
        "key": "RATE_LOCK_MINUTES",
        "value": "15",
        "value_type": "INT",
        "description": "Aynı kullanıcı + kutu kombinasyonu için bekleme süresi.",
    },
    # Şüphe sistemi
    {
        "key": "SUSPICION_VETTING_THRESHOLD",
        "value": "40",
        "value_type": "INT",
        "description": "Şüphe skoru bu değere ulaşınca kitle denetimine gönderilir.",
    },
    {
        "key": "SUSPICION_REJECT_THRESHOLD",
        "value": "100",
        "value_type": "INT",
        "description": "Şüphe skoru bu değere ulaşınca otomatik reddedilir.",
    },
    # Doluluk eşikleri
    {
        "key": "FILL_NOTICE_THRESHOLD",
        "value": "0.50",
        "value_type": "FLOAT",
        "description": "Dikkat eşiği: Lojistik panosu sarıya döner.",
    },
    {
        "key": "FILL_WARN_THRESHOLD",
        "value": "0.75",
        "value_type": "FLOAT",
        "description": "Uyarı eşiği: Sorumlu personele bildirim gönderilir.",
    },
    {
        "key": "FILL_CRITICAL_THRESHOLD",
        "value": "0.90",
        "value_type": "FLOAT",
        "description": "Kritik eşik: Acil bildirim + öğrenci yönlendirmesi.",
    },
    # Soft-sensing parametreleri
    {
        "key": "DECAY_RATE_PER_HOUR",
        "value": "0.002",
        "value_type": "FLOAT",
        "description": "Sıkışma düzeltme oranı (saat başına). fill_level'i çok az düşürür.",
    },
    {
        "key": "DECAY_MAX_CORRECTION",
        "value": "0.15",
        "value_type": "FLOAT",
        "description": "Maksimum toplam sıkışma düzeltmesi (oran, 0-1).",
    },
    {
        "key": "STAGNATION_ALERT_HOURS",
        "value": "4",
        "value_type": "INT",
        "description": "Dolu kutu (≥0.75) bu kadar saat hareketsiz kalırsa alarm üretilir.",
    },
    # Anomali dedektörü
    {
        "key": "ANOMALY_SIGMA_MULTIPLIER",
        "value": "3",
        "value_type": "INT",
        "description": "Anomali eşiği: μ + N×σ. Saatlik bildirim sayısı bu eşiği aşarsa dondurulur.",
    },
    {
        "key": "ANOMALY_HISTORY_DAYS",
        "value": "30",
        "value_type": "INT",
        "description": "Anomali hesabında kullanılacak geçmiş gün sayısı.",
    },
    # Offline sync
    {
        "key": "CLIENT_TIMESTAMP_MAX_DIFF_HOURS",
        "value": "24",
        "value_type": "INT",
        "description": "client_timestamp ile sunucu zamanı farkı bu saati aşarsa time-spoofing: otomatik red.",
    },
    # AI
    {
        "key": "DAILY_TOKEN_LIMIT",
        "value": "50000",
        "value_type": "INT",
        "description": "Kullanıcı başına günlük OpenAI token limiti.",
    },
    {
        "key": "AI_PHOTO_VETTING_ENABLED",
        "value": "true",
        "value_type": "BOOL",
        "description": "Vision API fotoğraf analizini aç/kapat. Kapalıysa suspicion +10 eklenir.",
    },
    {
        "key": "AI_COACH_ENABLED",
        "value": "true",
        "value_type": "BOOL",
        "description": "Haftalık AI koç mesajlarını aç/kapat.",
    },
    # Bounty
    {
        "key": "BOUNTY_DEFAULT_MAX_CLAIMANTS",
        "value": "3",
        "value_type": "INT",
        "description": "Varsayılan maksimum bounty kazanan sayısı.",
    },
    {
        "key": "BOUNTY_SYSTEM_ENABLED",
        "value": "true",
        "value_type": "BOOL",
        "description": "Tüm bounty sistemini aç/kapat.",
    },
    # Veri saklama
    {
        "key": "PHOTO_RETENTION_DAYS",
        "value": "30",
        "value_type": "INT",
        "description": "Fotoğraf dosyalarının saklanma süresi (gün). Celery task siler.",
    },
    {
        "key": "REPORT_RETENTION_DAYS",
        "value": "730",
        "value_type": "INT",
        "description": "Ham bildirim kayıtlarının saklanma süresi (gün = 2 yıl).",
    },
]
