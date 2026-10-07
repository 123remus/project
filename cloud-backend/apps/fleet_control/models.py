from django.db import models
from apps.sites.models import Site

class ControlLog(models.Model):
    """
    Tesla Fleet API 遠端控制稽核紀錄表 (對應架構圖中發送控制指令與稽核軌跡)
    """
    STATUS_CHOICES = (
        ('PENDING', '處理中'),
        ('SUCCESS', '執行成功'),
        ('FAILED', '執行失敗'),
    )

    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='control_logs', to_field='site_id', db_column='site_id')
    command_type = models.CharField(max_length=64, help_text="控制指令種類，如 backup_reserve, operation_mode")
    parameters = models.JSONField(default=dict, help_text="指令參數內容")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    tesla_command_id = models.CharField(max_length=128, blank=True, null=True, help_text="Tesla 官方回應指令 ID")
    tesla_response = models.JSONField(default=dict, blank=True, help_text="Tesla API 回傳完整原始 JSON")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'control_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.site_id}] {self.command_type} -> {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
