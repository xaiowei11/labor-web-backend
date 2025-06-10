from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta
from .models import ReminderSchedule, Worker, LineUserBinding, ReminderLog
from .line_bot_handler import LineBotService

@shared_task
def send_scheduled_reminders():
    """發送排程提醒"""
    now = timezone.now()
    current_time = now.time()
    current_weekday = now.weekday() + 1  # 1-7, 週一為1
    
    # 查找符合條件的排程
    schedules = ReminderSchedule.objects.filter(
        is_active=True,
        reminder_time__hour=current_time.hour,
        reminder_time__minute=current_time.minute
    )
    
    line_service = LineBotService()
    sent_count = 0
    
    for schedule in schedules:
        # 檢查是否為提醒日
        if schedule.frequency == 'daily' or current_weekday in schedule.reminder_days:
            # 獲取該公司所有綁定的勞工
            bindings = LineUserBinding.objects.filter(
                worker__company=schedule.company,
                is_active=True
            ).select_related('worker')
            
            for binding in bindings:
                # 檢查是否需要提醒
                if line_service.check_need_fill_form(binding.worker):
                    success = line_service.send_reminder_to_worker(binding.worker, schedule)
                    if success:
                        sent_count += 1
    
    return f"共發送 {sent_count} 個提醒"

@shared_task
def check_form_completion():
    """檢查表單完成狀態並更新記錄"""
    # 檢查最近24小時內點擊但未完成的提醒
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    logs = ReminderLog.objects.filter(
        status='clicked',
        clicked_at__gte=cutoff_time
    )
    
    for log in logs:
        # 檢查是否有新的表單提交
        latest_submission = log.worker.formsubmission_set.filter(
            submission_time__gte=log.clicked_at
        ).first()
        
        if latest_submission:
            log.status = 'completed'
            log.completed_at = latest_submission.submission_time
            log.save()

@shared_task
def smart_reminder_check():
    """智能提醒檢查 - 根據實際填寫狀態決定是否提醒"""
    line_service = LineBotService()
    
    # 獲取所有啟用的綁定用戶
    active_bindings = LineUserBinding.objects.filter(is_active=True).select_related('worker')
    
    reminder_sent = 0
    
    for binding in active_bindings:
        worker = binding.worker
        
        # 檢查是否需要提醒
        reminder_check = line_service.handle_smart_reminder_check(worker)

        if reminder_check['needs_reminder']:
            # 發送個人化提醒
            try:
                form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
                flex_message = line_service.create_form_flex_message(worker, form_url)
                
                line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
                reminder_sent += 1
                
            except Exception as e:
                print(f"發送提醒失敗 {worker.name}: {e}")
    
    return f"智能提醒：共發送 {reminder_sent} 個提醒"

@shared_task
def daily_status_report():
    """每日狀態報告 - 發送給綁定用戶"""
    from linebot.models import TextSendMessage
    
    line_service = LineBotService()
    active_bindings = LineUserBinding.objects.filter(is_active=True).select_related('worker')
    
    for binding in active_bindings:
        worker = binding.worker
        status_info = line_service.get_worker_status_detailed(worker)
        status_message = line_service.create_status_message(worker, status_info)
        
        try:
            line_service.line_bot_api.push_message(
                binding.line_user_id,
                TextSendMessage(text=f"📊 每日狀態報告\n\n{status_message}")
            )
        except Exception as e:
            print(f"發送狀態報告失敗 {worker.name}: {e}")