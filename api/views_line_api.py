from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import Worker, FormSubmission, LineUserBinding, Company, ReminderLog
from .line_bot_handler import LineBotService

@api_view(['GET'])
@permission_classes([AllowAny])
def check_worker_status_api(request):
    """API 端點：檢查勞工填寫狀態（供 LINE Bot 使用）"""
    worker_code = request.GET.get('worker_code')
    company_code = request.GET.get('company_code')
    
    if not worker_code or not company_code:
        return Response({'error': '缺少必要參數'}, status=400)
    
    try:
        company = Company.objects.get(code=company_code)
        worker = Worker.objects.get(code=worker_code, company=company)
        
        line_service = LineBotService()
        status_info = line_service.get_worker_status_detailed(worker)
        
        return Response({
            'worker_name': worker.name,
            'company_name': company.name,
            'status': status_info
        })
        
    except (Company.DoesNotExist, Worker.DoesNotExist):
        return Response({'error': '勞工或公司不存在'}, status=404)

@api_view(['POST'])
@permission_classes([AllowAny])
def line_bot_query(request):
    """專門給 LINE Bot 使用的查詢端點"""
    line_user_id = request.data.get('line_user_id')
    query_type = request.data.get('query_type')  # 'status', 'history', 'check_reminder'
    
    try:
        binding = LineUserBinding.objects.get(line_user_id=line_user_id)
        worker = binding.worker
        line_service = LineBotService()
        
        if query_type == 'status':
            result = line_service.get_worker_status_detailed(worker)
        elif query_type == 'history':
            result = line_service.get_filling_history(worker)
        elif query_type == 'check_reminder':
            result = line_service.handle_smart_reminder_check(worker)
        else:
            return Response({'error': '無效的查詢類型'}, status=400)
        
        return Response({
            'worker_name': worker.name,
            'data': result
        })
        
    except LineUserBinding.DoesNotExist:
        return Response({'error': '用戶未綁定'}, status=404)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def test_line_reminder(request):
    """測試 LINE 提醒功能"""
    action = request.data.get('action', 'smart')  # 'smart', 'all', 'specific'
    
    try:
        if action == 'smart':
            # 測試智能提醒
            from .tasks import smart_reminder_check
            result = smart_reminder_check()
            
        elif action == 'all':
            # 測試發送給所有綁定用戶
            line_service = LineBotService()
            sent_count = 0
            
            bindings = LineUserBinding.objects.filter(is_active=True)
            for binding in bindings:
                try:
                    form_url = f"{settings.FRONTEND_URL}/form?worker_code={binding.worker.code}&company_code={binding.worker.company.code}"
                    flex_message = line_service.create_form_flex_message(binding.worker, form_url)
                    line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
                    sent_count += 1
                except Exception as e:
                    print(f"發送失敗給 {binding.worker.name}: {e}")
            
            result = f"已發送測試提醒給 {sent_count} 位用戶"
            
        elif action == 'specific':
            # 測試發送給特定用戶
            worker_code = request.data.get('worker_code')
            company_code = request.data.get('company_code')
            
            if not worker_code or not company_code:
                return Response({'error': '缺少 worker_code 或 company_code'}, status=400)
            
            company = Company.objects.get(code=company_code)
            worker = Worker.objects.get(code=worker_code, company=company)
            binding = LineUserBinding.objects.get(worker=worker, is_active=True)
            
            line_service = LineBotService()
            form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
            flex_message = line_service.create_form_flex_message(worker, form_url)
            line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
            
            result = f"已發送測試提醒給 {worker.name}"
        
        else:
            return Response({'error': '無效的 action'}, status=400)
        
        return Response({
            'success': True,
            'message': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def line_system_status(request):
    """檢查 LINE Bot 系統狀態"""
    try:
        # 檢查綁定用戶數量
        total_bindings = LineUserBinding.objects.count()
        active_bindings = LineUserBinding.objects.filter(is_active=True).count()
        
        # 檢查最近的提醒記錄
        recent_logs = ReminderLog.objects.filter(
            sent_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # 檢查 LINE Bot 設定
        line_config_ok = bool(settings.LINE_CHANNEL_ACCESS_TOKEN and settings.LINE_CHANNEL_SECRET)
        
        return Response({
            'system_status': 'OK',
            'line_config': line_config_ok,
            'total_bindings': total_bindings,
            'active_bindings': active_bindings,
            'reminders_24h': recent_logs,
            'frontend_url': settings.FRONTEND_URL,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'system_status': 'ERROR',
            'error': str(e)
        }, status=500)
    
@api_view(['POST'])
@permission_classes([AllowAny])
def trigger_smart_reminders(request):
    """手動觸發智能提醒 - 測試用"""
    try:
        from .tasks import smart_reminder_check
        # 直接呼叫任務函數（不透過 Celery）
        result = smart_reminder_check()
        
        return Response({
            'success': True,
            'message': result
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['POST']) 
@permission_classes([AllowAny])
def test_specific_worker_reminder(request):
    """測試特定勞工提醒"""
    worker_code = request.data.get('worker_code')
    company_code = request.data.get('company_code')
    
    if not worker_code or not company_code:
        return Response({'error': '缺少必要參數'}, status=400)
    
    try:
        company = Company.objects.get(code=company_code)
        worker = Worker.objects.get(code=worker_code, company=company)
        
        # 檢查綁定狀態
        try:
            binding = LineUserBinding.objects.get(worker=worker, is_active=True)
        except LineUserBinding.DoesNotExist:
            return Response({'error': '該勞工尚未綁定 LINE'}, status=400)
        
        # 發送測試提醒
        line_service = LineBotService()
        
        # 檢查是否需要提醒
        reminder_check = line_service.handle_smart_reminder_check(worker)
        
        if reminder_check['needs_reminder']:
            # 生成表單連結並發送
            from django.conf import settings
            form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
            flex_message = line_service.create_form_flex_message(worker, form_url)
            line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
            
            return Response({
                'success': True,
                'message': f'已發送提醒給 {worker.name}',
                'reminder_info': reminder_check
            })
        else:
            return Response({
                'success': True,
                'message': f'{worker.name} 目前不需要提醒',
                'reminder_info': reminder_check
            })
            
    except (Company.DoesNotExist, Worker.DoesNotExist):
        return Response({'error': '勞工或公司不存在'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_line_reminder(request):
    """測試 LINE 提醒功能"""
    action = request.data.get('action', 'smart')  # 'smart', 'all', 'specific'
    
    try:
        if action == 'smart':
            # 測試智能提醒
            from .tasks import smart_reminder_check
            result = smart_reminder_check()
            
        elif action == 'all':
            # 測試發送給所有綁定用戶
            line_service = LineBotService()
            sent_count = 0
            
            bindings = LineUserBinding.objects.filter(is_active=True)
            for binding in bindings:
                try:
                    from django.conf import settings
                    form_url = f"{settings.FRONTEND_URL}/form?worker_code={binding.worker.code}&company_code={binding.worker.company.code}"
                    flex_message = line_service.create_form_flex_message(binding.worker, form_url)
                    line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
                    sent_count += 1
                except Exception as e:
                    print(f"發送失敗給 {binding.worker.name}: {e}")
            
            result = f"已發送測試提醒給 {sent_count} 位用戶"
            
        elif action == 'specific':
            # 測試發送給特定用戶
            worker_code = request.data.get('worker_code')
            company_code = request.data.get('company_code')
            
            if not worker_code or not company_code:
                return Response({'error': '缺少 worker_code 或 company_code'}, status=400)
            
            company = Company.objects.get(code=company_code)
            worker = Worker.objects.get(code=worker_code, company=company)
            binding = LineUserBinding.objects.get(worker=worker, is_active=True)
            
            line_service = LineBotService()
            from django.conf import settings
            form_url = f"{settings.FRONTEND_URL}/form?worker_code={worker.code}&company_code={worker.company.code}"
            flex_message = line_service.create_form_flex_message(worker, form_url)
            line_service.line_bot_api.push_message(binding.line_user_id, flex_message)
            
            result = f"已發送測試提醒給 {worker.name}"
        
        else:
            return Response({'error': '無效的 action'}, status=400)
        
        return Response({
            'success': True,
            'message': result,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def line_system_status(request):
    """檢查 LINE Bot 系統狀態"""
    try:
        # 檢查綁定用戶數量
        total_bindings = LineUserBinding.objects.count()
        active_bindings = LineUserBinding.objects.filter(is_active=True).count()
        
        # 檢查最近的提醒記錄
        try:
            from .models import ReminderLog
            from datetime import timedelta
            recent_logs = ReminderLog.objects.filter(
                sent_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
        except:
            # 如果 ReminderLog 模型不存在，設為 0
            recent_logs = 0
        
        # 檢查 LINE Bot 設定
        from django.conf import settings
        line_config_ok = bool(settings.LINE_CHANNEL_ACCESS_TOKEN and settings.LINE_CHANNEL_SECRET)
        
        return Response({
            'system_status': 'OK',
            'line_config': line_config_ok,
            'total_bindings': total_bindings,
            'active_bindings': active_bindings,
            'reminders_24h': recent_logs,
            'frontend_url': settings.FRONTEND_URL,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'system_status': 'ERROR',
            'error': str(e)
        }, status=500)