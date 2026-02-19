from __future__ import annotations

from config.models import SystemSetting
from reports.models import CATEGORY_BASE_VOLUME


class WasteMathService:
    """
    Soft-Sensing matematiksel modeli.

    Sorumluluk: Bir WasteReport için fill_delta değerini hesaplar.
    Bu sınıf saf fonksiyonlar içerir; veritabanına yazma yapmaz.
    Yazma işlemi signal katmanına bırakılmıştır.

    Formül:
        fill_delta = base_volume × decay_correction_factor

    decay_correction_factor:
        Kutunun zaten çok dolu olduğu durumlarda gerçek doluluk
        artışı daha az olur (sıkışma etkisi).
        Henüz fiziksel kalibrasyon verisi olmadığı için şimdilik 1.0
        (yani düzeltme yok). Faz 2'de gerçek veriyle kalibre edilecek.

    Tüm eşik değerleri SystemSetting üzerinden okunur.
    Anahtar bulunamazsa models.py'deki CATEGORY_BASE_VOLUME sabiti
    fallback olarak kullanılır.
    """

    # Kategori override anahtarı: SystemSetting'de
    # BASE_VOLUME_<CATEGORY> formatında saklanabilir.
    _SETTING_PREFIX = "BASE_VOLUME_"

    @classmethod
    def get_base_volume(cls, waste_category: str) -> float:
        """
        Atık kategorisine göre temel hacim artış değerini döndürür.

        Önce SystemSetting'e bakar (runtime override için).
        Yoksa models.py'deki sabit sözlüğü kullanır.
        """
        setting_key = f"{cls._SETTING_PREFIX}{waste_category}"
        from_setting = SystemSetting.get(setting_key, default=None)

        if from_setting is not None:
            return float(from_setting)

        return CATEGORY_BASE_VOLUME.get(waste_category, 0.05)

    @classmethod
    def compute_fill_delta(
        cls,
        waste_category: str,
        current_fill_level: float = 0.0,
    ) -> float:
        """
        Bir bildirim için fill_delta hesaplar.

        Args:
            waste_category:    WasteCategory değeri (örn. 'PLASTIC').
            current_fill_level: Kutunun mevcut doluluk seviyesi (0.0–1.0).
                                Sıkışma düzeltmesi için kullanılır.

        Returns:
            Kutu fill_level'ına eklenecek delta (0.000–1.000 aralığında).
        """
        base_volume = cls.get_base_volume(waste_category)
        decay_correction = cls._decay_correction_factor(current_fill_level)
        delta = base_volume * decay_correction

        # Delta hiçbir zaman kutunun kalan kapasitesini aşmamalı.
        remaining = max(0.0, 1.0 - current_fill_level)
        return round(min(delta, remaining), 3)

    @staticmethod
    def _decay_correction_factor(current_fill_level: float) -> float:
        """
        Doluluk arttıkça sıkışma etkisi nedeniyle gerçek hacim artışı azalır.

        Faz 1 kalibrasyonu:
            0.00 – 0.74 → düzeltme yok (1.0)
            0.75 – 0.89 → hafif sıkışma (0.85)
            0.90 – 1.00 → belirgin sıkışma (0.60)

        Bu katsayılar ilerleyen fazlarda saha verisiyle güncellenir.
        """
        if current_fill_level >= 0.90:
            return 0.60
        if current_fill_level >= 0.75:
            return 0.85
        return 1.0
