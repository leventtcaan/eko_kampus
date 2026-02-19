from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="reports.WasteReport")
def on_wastereport_created(sender, instance, created: bool, **kwargs) -> None:
    """
    Yeni WasteReport oluşturulduğunda tetiklenir.

    Adımlar:
        1. WasteMathService ile fill_delta hesapla.
        2. fill_delta değerini rapora kaydet (update — post_save döngüsünü önler).
        3. Bin.add_fill() ile kutunun fill_level'ını atomik artır.
           → Bin.add_fill() zaten BinStatusLog kaydı oluşturur.

    Neden update() ve save() değil?
        save() çağrısı bu sinyali yeniden tetikler → sonsuz döngü.
        Sadece fill_delta alanını hedefleyen update() kullanılır.
    """
    if not created:
        return

    # Import burada yapılıyor; uygulama başlangıcında circular import'u önler.
    from campus.services import WasteMathService

    bin_obj = instance.bin

    try:
        # Güncel fill_level'ı DB'den oku (race condition önlemi).
        bin_obj.refresh_from_db(fields=["fill_level"])
        current_fill = float(bin_obj.fill_level)

        fill_delta = WasteMathService.compute_fill_delta(
            waste_category=instance.waste_category,
            current_fill_level=current_fill,
        )

        # fill_delta'yı rapora kaydet — save() değil update() kullanıyoruz.
        from reports.models import WasteReport
        WasteReport.objects.filter(pk=instance.pk).update(fill_delta=fill_delta)
        instance.fill_delta = fill_delta  # instance'ı da güncelle (bellekte tutarlılık).

        # Kutunun doluluk seviyesini atomik artır + BinStatusLog oluştur.
        bin_obj.add_fill(delta=fill_delta, triggered_by=instance.user)

        logger.info(
            "WasteReport %s → fill_delta=%.3f | Bin %s fill_level=%.3f",
            instance.pk,
            fill_delta,
            bin_obj.code,
            float(bin_obj.fill_level),
        )

    except Exception:
        # Sinyal hatası ana isteği engellememelidir.
        logger.exception(
            "WasteReport post_save sinyali başarısız. report_id=%s", instance.pk
        )
