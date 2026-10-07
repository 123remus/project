from django.db import models
from apps.sites.models import Site

class TelemetryRecord(models.Model):
    """
    遙測時間序列資料表 (在 TimescaleDB 中由 SQL 初始化轉為 Hypertable)
    """
    time = models.DateTimeField(db_index=True, help_text="採集時間戳記")
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='telemetry', to_field='site_id', db_column='site_id')
    solar_kw = models.FloatField(default=0.0, help_text="太陽能功率 (kW)")
    grid_kw = models.FloatField(default=0.0, help_text="電網功率 (kW, 負值為回售)")
    battery_kw = models.FloatField(default=0.0, help_text="電池功率 (kW, 正值充電, 負值放電)")
    home_kw = models.FloatField(default=0.0, help_text="家庭負載用電 (kW)")
    soc_pct = models.FloatField(default=0.0, help_text="電池電量百分比 (%)")
    grid_status = models.CharField(max_length=32, default="Connected")
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'telemetry_records'
        ordering = ['-time']
        indexes = [
            models.Index(fields=['site', '-time']),
        ]

    def __str__(self):
        return f"[{self.site_id}] {self.time}: Solar={self.solar_kw}kW, Batt={self.battery_kw}kW, SoC={self.soc_pct}%"
