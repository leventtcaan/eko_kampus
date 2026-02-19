# =============================================================================
# ai_logs/models.py
#
# Django App: ai_logs
# Bağımlılıklar: accounts
#
# Her OpenAI API çağrısının tam kayıt defteri.
# Amaçlar:
#   1. Maliyet takibi: Günlük/aylık API harcaması.
#   2. Kullanıcı bazlı token limiti: Günlük 50,000 token aşılırsa erişim kesilir.
#   3. Latency takibi: Hangi feature yavaş? Önce hangisini optimize et?
#   4. Hata analizi: Hangi promptlar API hatasına neden oluyor?
#   5. Model karşılaştırması: gpt-4o-mini vs gpt-4o maliyet/kalite dengesi.
# =============================================================================

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class AIFeature(models.TextChoices):
    """
    Hangi özellik bu API çağrısını yaptı?
    Yeni AI özelliği eklendiğinde buraya eklenir.
    """

    PHOTO_VETTING = "PHOTO_VETTING", _("Fotoğraf Doğrulama (WasteReport)")
    DETECTIVE_ANALYSIS = "DETECTIVE_ANALYSIS", _("Fotoğraf Analizi (DetectiveReport)")
    AI_COACH = "AI_COACH", _("AI Davranış Koçu")
    PRIORITY_ADVISOR = "PRIORITY_ADVISOR", _("Öncelik Danışmanı")
    SMART_CATEGORIZE = "SMART_CATEGORIZE", _("Akıllı Kategorizasyon")
    CARBON_CALC = "CARBON_CALC", _("Karbon Hesaplama")


class AIAnalysisLog(models.Model):
    """
    Tek bir OpenAI API çağrısının kaydı.

    cost_usd hesabı (view/service katmanında yapılır):
        gpt-4o-mini: input $0.15/1M token, output $0.60/1M token
        Bu değerler SystemSetting'den okunmalı; fiyatlar değişebilir.

    Günlük token limiti kontrolü (view katmanında):
        Bugün kullanıcının kullandığı toplam token:
        AIAnalysisLog.objects
            .filter(user=user, created_at__date=today)
            .aggregate(total=Sum('tokens_input') + Sum('tokens_output'))
        Bu toplamı SystemSetting.DAILY_TOKEN_LIMIT ile karşılaştır.

    related_object_type / related_object_id:
        "Bu API çağrısı hangi kayıt için yapıldı?"
        Örn: PHOTO_VETTING için WasteReport UUID'si.
        Debug: "Bu raporun vision analiz sonucu neydi?"
    """

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_logs",
        verbose_name=_("Kullanıcı"),
        help_text=_("Sistem otomatik çağrıları için None (koç mesajları hariç)."),
    )
    feature = models.CharField(
        _("Özellik"),
        max_length=40,
        choices=AIFeature.choices,
    )
    model_used = models.CharField(
        _("Kullanılan Model"),
        max_length=30,
        default="gpt-4o-mini",
        help_text=_("Örn: gpt-4o-mini, gpt-4o"),
    )

    tokens_input = models.PositiveIntegerField(_("Girdi Token"))
    tokens_output = models.PositiveIntegerField(_("Çıktı Token"))
    cost_usd = models.DecimalField(
        _("Maliyet (USD)"),
        max_digits=10,
        decimal_places=6,
        help_text=_(
            "(tokens_input * input_price + tokens_output * output_price) / 1_000_000"
        ),
    )
    response_time_ms = models.PositiveIntegerField(
        _("Yanıt Süresi (ms)"),
        help_text=_("API çağrısının toplam süresi. Latency takibi için."),
    )

    success = models.BooleanField(_("Başarılı"), default=True)
    error_code = models.CharField(
        _("Hata Kodu"),
        max_length=50,
        blank=True,
        help_text=_("API hata döndürdüyse: rate_limit_error, invalid_api_key, vb."),
    )

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

    created_at = models.DateTimeField(_("Zaman"), auto_now_add=True)

    class Meta:
        verbose_name = _("AI Analiz Günlüğü")
        verbose_name_plural = _("AI Analiz Günlükleri")
        ordering = ["-created_at"]
        indexes = [
            # Günlük token limiti kontrolü: "Kullanıcı bugün kaç token kullandı?"
            models.Index(fields=["user", "-created_at"], name="idx_ailog_user_date"),
            # Özellik bazlı maliyet analizi: "Vision analizi ne kadar tutuyor?"
            models.Index(
                fields=["feature", "-created_at"], name="idx_ailog_feature_date"
            ),
            # Hata oranı takibi: "Son 24 saatte kaç başarısız çağrı var?"
            models.Index(
                fields=["success", "-created_at"], name="idx_ailog_success_date"
            ),
            # Model bazlı maliyet: "gpt-4o kullanımı toplamda ne kadar?"
            models.Index(
                fields=["model_used", "-created_at"], name="idx_ailog_model_date"
            ),
        ]

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return (
            f"[{status}] {self.get_feature_display()} | "
            f"{self.model_used} | "
            f"{self.tokens_input + self.tokens_output} token | "
            f"${self.cost_usd:.4f}"
        )

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output
