from django.db import models

class Site(models.Model):
    """
    案場中繼資料表 (儲存案場名稱、TEG 區域網路 IP、電池規格等)
    """
    site_id = models.CharField(max_length=64, primary_key=True, help_text="案場識別碼，如 site_01")
    name = models.CharField(max_length=128, help_text="案場名稱")
    teg_ip = models.CharField(max_length=64, default="192.168.1.100", help_text="案場 TEG 區域網路 IP")
    battery_capacity_kwh = models.FloatField(default=13.5, help_text="電池額定總容量 (kWh)")
    max_solar_kw = models.FloatField(default=10.0, help_text="太陽能最大裝置容量 (kW)")
    timezone = models.CharField(max_length=64, default="Asia/Taipei")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sites'
        ordering = ['site_id']

    def __str__(self):
        return f"{self.name} ({self.site_id})"
