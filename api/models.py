from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import os


def experiment_file_upload_path(instance, filename):
    """定義實驗檔案上傳路徑"""
    return f'experiment_files/{instance.experiment.id}/{filename}'


class Company(models.Model):
    name = models.CharField(max_length=100, verbose_name="公司名稱")
    code = models.CharField(max_length=10, unique=True, verbose_name="公司代碼")
    is_super_company = models.BooleanField(default=False, verbose_name="是否為超級實驗公司")
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name = "公司"
        verbose_name_plural = "公司"
   

# 勞工模型
class Worker(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        unique_together = ('company', 'code')  # 確保在同一公司內勞工代碼唯一


# 實驗紀錄模型
class Experiment(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    experimenter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    experiment_time = models.DateTimeField()
    experiment_type = models.CharField(max_length=50)
    data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.worker.name} - {self.experiment_type} - {self.experiment_time}"


# 實驗檔案模型
class ExperimentFile(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='files')
    file_field_name = models.CharField(max_length=100, help_text="表單中的檔案欄位名稱")
    file = models.FileField(upload_to=experiment_file_upload_path)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.experiment} - {self.file_field_name}"
    
    def get_file_url(self):
        """獲取檔案的完整 URL"""
        if self.file:
            return self.file.url
        return None


# 表單類型模型
class FormType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_required_first_time = models.BooleanField(default=True)
    is_required_subsequent = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


# 表單紀錄模型
class FormSubmission(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    form_type = models.ForeignKey(FormType, on_delete=models.CASCADE)
    submission_time = models.DateTimeField(auto_now_add=True)
    submission_count = models.IntegerField()  # 第幾次填寫
    time_segment = models.IntegerField(default=1)
    stage = models.IntegerField(default=0)  # 階段字段
    data = models.JSONField()  # 存儲表單數據

    def __str__(self):
        return f"{self.worker.name} - {self.form_type.name} - 第{self.submission_count}次"


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', '超級管理員'),
        ('owner', '公司老闆'),
        ('admin', '公司管理員'),
        ('experimenter', '實驗者'),
        ('super_experimenter', '超級實驗者'),
    )
    login_code = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="登入帳號")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, verbose_name="所屬公司")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin', verbose_name="角色")
    full_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="真實姓名")
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = "用戶"
        verbose_name_plural = "用戶"

## line bot
class LineUserBinding(models.Model):
    """LINE 用戶綁定模型"""
    worker = models.OneToOneField(Worker, on_delete=models.CASCADE, related_name='line_binding')
    line_user_id = models.CharField(max_length=100, unique=True, verbose_name="LINE User ID")
    is_active = models.BooleanField(default=True, verbose_name="是否啟用提醒")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "LINE用戶綁定"
        verbose_name_plural = "LINE用戶綁定"
    
    def __str__(self):
        return f"{self.worker.name} - {self.line_user_id}"

class ReminderSchedule(models.Model):
    """提醒排程模型"""
    FREQUENCY_CHOICES = [
        ('daily', '每日'),
        ('weekly', '每週'),
        ('monthly', '每月'),
        ('custom', '自定義'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name="排程名稱")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='weekly')
    reminder_time = models.TimeField(verbose_name="提醒時間")
    reminder_days = models.JSONField(default=list, help_text="週幾提醒 [1-7]，1為週一")
    message_template = models.TextField(verbose_name="提醒訊息模板")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "提醒排程"
        verbose_name_plural = "提醒排程"

class ReminderLog(models.Model):
    """提醒記錄模型"""
    STATUS_CHOICES = [
        ('sent', '已發送'),
        ('failed', '發送失敗'),
        ('clicked', '已點擊'),
        ('completed', '已完成填寫'),
    ]
    
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    schedule = models.ForeignKey(ReminderSchedule, on_delete=models.CASCADE, null=True, blank=True)  # 允許 null
    message_content = models.TextField(verbose_name="發送內容")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    sent_at = models.DateTimeField(auto_now_add=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "提醒記錄"
        verbose_name_plural = "提醒記錄"
