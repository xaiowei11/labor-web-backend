import os
from datetime import timedelta
from linebot import LineBotApi, WebhookHandler
from linebot.models import *
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db import models
from .models import LineUserBinding, Worker, Company, FormSubmission, ReminderLog

class LineBotService:
    def __init__(self):
        self.line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
        self.handler = WebhookHandler(settings.LINE_CHANNEL_SECRET)
        
    def handle_message(self, event):
        """處理用戶訊息 - 擴展版本"""
        user_id = event.source.user_id
        message_text = event.message.text.strip()
        
        # 檢查是否為綁定指令
        if message_text.startswith('綁定'):
            self.handle_binding(event, message_text)
        elif message_text == '查詢狀態' or message_text == '狀態':
            self.handle_status_query(event)
        elif message_text == '詳細狀態' or message_text == '歷史記錄':
            self.handle_detailed_status(event)
        elif message_text == '填寫問卷' or message_text == '立即填寫':
            self.handle_form_request(event)
        elif message_text == '取消提醒':
            self.handle_unsubscribe(event)
        elif message_text == '幫助' or message_text == '說明':
            self.send_help_message(event)
        else:
            self.send_help_message(event)
    
    def handle_binding(self, event, message_text):
        """處理綁定功能"""
        try:
            # 解析綁定指令: "綁定 公司代碼 勞工代碼"
            parts = message_text.split()
            if len(parts) != 3:
                self.reply_message(event, "綁定格式錯誤！請使用：綁定 公司代碼 勞工代碼")
                return
            
            company_code = parts[1]
            worker_code = parts[2]
            user_id = event.source.user_id
            
            # 查找公司和勞工
            try:
                company = Company.objects.get(code=company_code)
                worker = Worker.objects.get(code=worker_code, company=company)
            except Company.DoesNotExist:
                self.reply_message(event, "公司代碼不存在！")
                return
            except Worker.DoesNotExist:
                self.reply_message(event, "勞工代碼不存在或不屬於此公司！")
                return
            
            # 創建或更新綁定
            binding, created = LineUserBinding.objects.get_or_create(
                worker=worker,
                defaults={'line_user_id': user_id}
            )
            
            if not created:
                binding.line_user_id = user_id
                binding.is_active = True
                binding.save()
            
            self.reply_message(event, f"綁定成功！\n勞工：{worker.name}\n公司：{company.name}\n\n您將會收到問卷填寫提醒。")
            
        except Exception as e:
            self.reply_message(event, f"綁定失敗：{str(e)}")
    
    def handle_status_query(self, event):
        """詳細的填寫狀態查詢"""
        user_id = event.source.user_id
        
        try:
            binding = LineUserBinding.objects.get(line_user_id=user_id)
            worker = binding.worker
            
            # 獲取詳細的填寫狀態
            status_info = self.get_worker_status_detailed(worker)
            
            # 創建狀態回報訊息
            status_message = self.create_status_message(worker, status_info)
            
            # 如果有未完成的表單，提供快速填寫選項
            if status_info['needs_fill']:
                quick_reply = QuickReply(items=[
                    QuickReplyButton(action=MessageAction(label="立即填寫", text="填寫問卷")),
                    QuickReplyButton(action=MessageAction(label="查看詳情", text="詳細狀態")),
                    QuickReplyButton(action=MessageAction(label="幫助", text="幫助"))
                ])
                
                self.line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=status_message, quick_reply=quick_reply)
                )
            else:
                self.reply_message(event, status_message)
                
        except LineUserBinding.DoesNotExist:
            self.send_binding_instruction(event)
    
    def handle_form_request(self, event):
        """處理填寫問卷請求"""
        user_id = event.source.user_id
        
        try:
            binding = LineUserBinding.objects.get(line_user_id=user_id)
            worker = binding.worker
            
            # 生成問卷連結
            form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
            
            # 創建豐富訊息
            flex_message = self.create_form_flex_message(worker, form_url)
            self.line_bot_api.reply_message(event.reply_token, flex_message)
            
            # 記錄點擊
            self.log_reminder_clicked(worker)
            
        except LineUserBinding.DoesNotExist:
            self.reply_message(event, "您尚未綁定勞工帳號，請先進行綁定。")
    
    def handle_unsubscribe(self, event):
        """處理取消提醒"""
        user_id = event.source.user_id
        
        try:
            binding = LineUserBinding.objects.get(line_user_id=user_id)
            binding.is_active = False
            binding.save()
            
            self.reply_message(event, "已取消問卷提醒。如需重新啟用，請重新綁定。")
            
        except LineUserBinding.DoesNotExist:
            self.reply_message(event, "您尚未綁定勞工帳號。")
    
    def send_help_message(self, event):
        """發送幫助訊息"""
        help_text = """歡迎使用勞工健康問卷提醒系統！

可用指令：
📝 綁定 公司代碼 勞工代碼 - 綁定您的勞工帳號
📊 查詢狀態 - 查看填寫狀態
📋 填寫問卷 - 獲取問卷連結
🔕 取消提醒 - 取消自動提醒

如有問題請聯繫公司管理員。"""
        self.reply_message(event, help_text)
    
    def reply_message(self, event, text):
        """回覆訊息"""
        self.line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=text)
        )
    
    def get_worker_status_detailed(self, worker):
        """獲取勞工的詳細填寫狀態"""
        now = timezone.now()
        today = now.date()
        current_hour = now.hour
        
        # 獲取最新的批次號
        latest_submission = FormSubmission.objects.filter(
            worker=worker
        ).order_by('-submission_time').first()
        
        current_batch = latest_submission.submission_count if latest_submission else 1
        
        # 判斷當前應該在哪個階段
        current_stage = self.determine_current_stage(current_hour)
        
        # 檢查今天各階段的填寫狀態
        today_submissions = FormSubmission.objects.filter(
            worker=worker,
            submission_time__date=today,
            submission_count=current_batch
        )
        
        # 分析各階段狀態
        stage_status = self.analyze_stage_status(today_submissions, current_stage)
        
        # 計算整體統計
        total_stats = self.calculate_total_stats(worker)
        
        return {
            'current_batch': current_batch,
            'current_stage': current_stage,
            'stage_status': stage_status,
            'needs_fill': stage_status['current_stage_incomplete'],
            'total_stats': total_stats,
            'last_submission': latest_submission
        }
    
    def determine_current_stage(self, hour):
        """根據當前時間判斷應該在哪個階段"""
        if 6 <= hour < 12:
            return 0  # 早上表單 (6-12點)
        elif 12 <= hour < 14:
            return 1  # 中午表單 (12-14點)
        elif 14 <= hour < 17:
            return 2  # 下午表單 (14-17點)
        elif 17 <= hour < 20:
            return 3  # 下班表單 (17-20點)
        else:
            return 4  # 晚上表單 (20點後)
    
    def analyze_stage_status(self, today_submissions, current_stage):
        """分析各階段的填寫狀態"""
        # 定義各階段需要的表單類型 (對應你的 STAGE_FORMS)
        STAGE_REQUIREMENTS = {
            0: [1, 2, 3],  # 早上：睡眠、嗜睡、視覺疲勞
            1: [2, 3],     # 中午：嗜睡、視覺疲勞
            2: [2, 3],     # 下午：嗜睡、視覺疲勞
            3: [2, 3],     # 下班：嗜睡、視覺疲勞
            4: [2, 3, 4]   # 晚上：嗜睡、視覺疲勞、NASA-TLX
        }
        
        stages_status = {}
        current_stage_incomplete = False
        
        for stage in range(5):
            required_forms = STAGE_REQUIREMENTS[stage]
            stage_submissions = today_submissions.filter(stage=stage)
            submitted_form_types = set(stage_submissions.values_list('form_type_id', flat=True))
            
            completed_forms = [form_id for form_id in required_forms if form_id in submitted_form_types]
            missing_forms = [form_id for form_id in required_forms if form_id not in submitted_form_types]
            
            stages_status[stage] = {
                'required': required_forms,
                'completed': completed_forms,
                'missing': missing_forms,
                'is_complete': len(missing_forms) == 0,
                'completion_rate': len(completed_forms) / len(required_forms) if required_forms else 1
            }
            
            # 檢查當前階段是否完成
            if stage == current_stage and not stages_status[stage]['is_complete']:
                current_stage_incomplete = True
        
        stages_status['current_stage_incomplete'] = current_stage_incomplete
        return stages_status
    
    def calculate_total_stats(self, worker):
        """計算總體統計資料"""
        total_submissions = FormSubmission.objects.filter(worker=worker).count()
        
        # 計算最近7天的填寫次數
        week_ago = timezone.now() - timedelta(days=7)
        recent_submissions = FormSubmission.objects.filter(
            worker=worker,
            submission_time__gte=week_ago
        ).count()
        
        # 計算當前批次進度
        current_batch = FormSubmission.objects.filter(
            worker=worker
        ).aggregate(max_batch=models.Max('submission_count'))['max_batch'] or 1
        
        # 計算當前批次已完成的階段數
        today = timezone.now().date()
        today_stages = FormSubmission.objects.filter(
            worker=worker,
            submission_time__date=today,
            submission_count=current_batch
        ).values('stage').distinct().count()
        
        return {
            'total_submissions': total_submissions,
            'recent_submissions': recent_submissions,
            'current_batch': current_batch,
            'today_completed_stages': today_stages,
            'first_submission_date': FormSubmission.objects.filter(
                worker=worker
            ).order_by('submission_time').first()
        }
    
    def create_status_message(self, worker, status_info):
        """創建詳細的狀態訊息"""
        stage_names = ["早上", "中午", "下午", "下班", "晚上"]
        form_names = {1: "睡眠調查", 2: "嗜睡量表", 3: "視覺疲勞", 4: "NASA-TLX"}
        
        message = f"📊 {worker.name} 的填寫狀態\n"
        message += f"公司：{worker.company.name}\n"
        message += f"當前批次：第 {status_info['current_batch']} 批\n\n"
        
        # 今日進度
        message += "📅 今日進度：\n"
        current_stage = status_info['current_stage']
        stage_status = status_info['stage_status']
        
        for stage in range(5):
            stage_info = stage_status[stage]
            status_icon = "✅" if stage_info['is_complete'] else "⏳" if stage == current_stage else "⚪"
            completion = f"({len(stage_info['completed'])}/{len(stage_info['required'])})"
            
            message += f"{status_icon} {stage_names[stage]} {completion}\n"
            
            # 顯示當前階段的詳細資訊
            if stage == current_stage and not stage_info['is_complete']:
                missing_forms = [form_names[form_id] for form_id in stage_info['missing']]
                message += f"   待填寫：{', '.join(missing_forms)}\n"
        
        # 總體統計
        stats = status_info['total_stats']
        message += f"\n📈 統計資料：\n"
        message += f"總填寫次數：{stats['total_submissions']} 次\n"
        message += f"近7天填寫：{stats['recent_submissions']} 次\n"
        
        # 最後填寫時間
        if status_info['last_submission']:
            last_time = status_info['last_submission'].submission_time
            message += f"最後填寫：{last_time.strftime('%m/%d %H:%M')}\n"
        
        # 提醒訊息
        if status_info['needs_fill']:
            message += f"\n⚠️ 請填寫{stage_names[current_stage]}表單！"
        else:
            message += f"\n🎉 {stage_names[current_stage]}階段已完成！"
        
        return message
    
    def handle_detailed_status(self, event):
        """處理詳細狀態查詢"""
        user_id = event.source.user_id
        
        try:
            binding = LineUserBinding.objects.get(line_user_id=user_id)
            worker = binding.worker
            
            # 獲取歷史填寫記錄
            history = self.get_filling_history(worker)
            
            # 創建歷史記錄訊息
            history_message = self.create_history_message(worker, history)
            
            self.reply_message(event, history_message)
            
        except LineUserBinding.DoesNotExist:
            self.send_binding_instruction(event)
    
    def get_filling_history(self, worker, days=7):
        """獲取最近幾天的填寫歷史"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        submissions = FormSubmission.objects.filter(
            worker=worker,
            submission_time__date__range=[start_date, end_date]
        ).order_by('-submission_time')
        
        # 按日期分組
        daily_submissions = {}
        for submission in submissions:
            date_key = submission.submission_time.date()
            if date_key not in daily_submissions:
                daily_submissions[date_key] = []
            daily_submissions[date_key].append(submission)
        
        return daily_submissions
    
    def create_history_message(self, worker, history):
        """創建歷史記錄訊息"""
        stage_names = ["早上", "中午", "下午", "下班", "晚上"]
        form_names = {1: "睡眠", 2: "嗜睡", 3: "視覺", 4: "TLX"}
        
        message = f"📋 {worker.name} 近7天填寫記錄\n\n"
        
        # 按日期顯示
        for i in range(7):
            date = timezone.now().date() - timedelta(days=i)
            date_str = date.strftime('%m/%d')
            
            if date in history:
                submissions = history[date]
                stages_filled = set(sub.stage for sub in submissions)
                stage_icons = []
                
                for stage in range(5):
                    if stage in stages_filled:
                        stage_icons.append("✅")
                    else:
                        stage_icons.append("⚪")
                
                message += f"{date_str}: {''.join(stage_icons)}\n"
                
                # 顯示詳細填寫時間
                for submission in sorted(submissions, key=lambda x: x.stage):
                    time_str = submission.submission_time.strftime('%H:%M')
                    form_name = form_names.get(submission.form_type_id, "其他")
                    message += f"  {stage_names[submission.stage]} {form_name} {time_str}\n"
            else:
                message += f"{date_str}: ⚪⚪⚪⚪⚪ (未填寫)\n"
        
        message += "\n圖例：✅已填寫 ⚪未填寫"
        return message
    
    def handle_smart_reminder_check(self, worker):
        """智能檢查是否需要提醒"""
        now = timezone.now()
        current_stage = self.determine_current_stage(now.hour)
        
        # 檢查當前階段是否已完成
        today_submissions = FormSubmission.objects.filter(
            worker=worker,
            submission_time__date=now.date(),
            stage=current_stage
        )
        
        # 獲取當前階段需要的表單類型
        STAGE_REQUIREMENTS = {
            0: [1, 2, 3], 1: [2, 3], 2: [2, 3], 3: [2, 3], 4: [2, 3, 4]
        }
        
        required_forms = STAGE_REQUIREMENTS.get(current_stage, [])
        submitted_forms = set(today_submissions.values_list('form_type_id', flat=True))
        
        missing_forms = [form_id for form_id in required_forms if form_id not in submitted_forms]
        
        return {
            'needs_reminder': len(missing_forms) > 0,
            'missing_forms': missing_forms,
            'current_stage': current_stage,
            'stage_name': ["早上", "中午", "下午", "下班", "晚上"][current_stage]
        }

    def send_binding_instruction(self, event):
        """發送綁定指示"""
        message = """🔗 請先綁定您的勞工帳號

使用方式：
綁定 公司代碼 勞工代碼

例如：
綁定 1111 001

綁定後即可查詢填寫狀態和接收提醒。
如有問題請聯繫公司管理員。"""
        self.reply_message(event, message)
    
    def create_form_flex_message(self, worker, form_url):
        """創建問卷 Flex Message"""
        flex_content = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "勞工健康問卷",
                        "weight": "bold",
                        "size": "xl",
                        "color": "#1f2937"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "text",
                                "text": f"勞工：{worker.name}",
                                "size": "md",
                                "color": "#6b7280"
                            },
                            {
                                "type": "text",
                                "text": f"公司：{worker.company.name}",
                                "size": "md",
                                "color": "#6b7280"
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "立即填寫問卷",
                            "uri": form_url
                        }
                    }
                ]
            }
        }
        
        return FlexSendMessage(alt_text="問卷填寫提醒", contents=flex_content)
    
    def check_need_fill_form(self, worker):
        """檢查是否需要填寫問卷"""
        # 這裡可以根據你的業務邏輯來判斷
        # 例如：檢查上次填寫時間是否超過一週
        latest_submission = FormSubmission.objects.filter(
            worker=worker
        ).order_by('-submission_time').first()
        
        if not latest_submission:
            return True
        
        # 如果超過一週沒填寫，需要提醒
        return timezone.now() - latest_submission.submission_time > timedelta(days=7)
    
    def log_reminder_clicked(self, worker):
        """記錄提醒點擊"""
        latest_log = ReminderLog.objects.filter(
            worker=worker,
            status='sent'
        ).order_by('-sent_at').first()
        
        if latest_log:
            latest_log.status = 'clicked'
            latest_log.clicked_at = timezone.now()
            latest_log.save()
    
    def send_reminder_to_worker(self, worker, schedule):
        """發送提醒給特定勞工"""
        try:
            binding = LineUserBinding.objects.get(worker=worker, is_active=True)
            
            # 生成個人化訊息
            message = schedule.message_template.format(
                worker_name=worker.name,
                company_name=worker.company.name
            )
            
            # 創建 Flex Message
            form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
            flex_message = self.create_form_flex_message(worker, form_url)
            
            # 發送訊息
            self.line_bot_api.push_message(binding.line_user_id, flex_message)
            
            # 記錄發送日誌
            ReminderLog.objects.create(
                worker=worker,
                schedule=schedule,
                message_content=message,
                status='sent'
            )
            
            return True
            
        except LineUserBinding.DoesNotExist:
            return False
        except LineBotApiError as e:
            print(f"LINE Bot API 錯誤: {e}")
            return False