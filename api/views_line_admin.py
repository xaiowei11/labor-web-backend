# api/views_line_admin.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import LineUserBinding, ReminderSchedule, ReminderLog
from .line_bot_handler import LineBotService
from .serializers import LineUserBindingSerializer, ReminderScheduleSerializer

class LineBindingListView(APIView):
    """獲取公司的 LINE 綁定列表"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['owner', 'admin']:
            return Response({"message": "權限不足"}, status=status.HTTP_403_FORBIDDEN)
        
        bindings = LineUserBinding.objects.filter(
            worker__company=request.user.company
        ).select_related('worker')
        
        serializer = LineUserBindingSerializer(bindings, many=True)
        return Response(serializer.data)

class ReminderScheduleView(APIView):
    """提醒排程管理"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['owner', 'admin']:
            return Response({"message": "權限不足"}, status=status.HTTP_403_FORBIDDEN)
        
        schedules = ReminderSchedule.objects.filter(company=request.user.company)
        serializer = ReminderScheduleSerializer(schedules, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        if request.user.role not in ['owner', 'admin']:
            return Response({"message": "權限不足"}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data.copy()
        data['company'] = request.user.company.id
        
        serializer = ReminderScheduleSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendTestReminderView(APIView):
    """發送測試提醒"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if request.user.role not in ['owner', 'admin']:
            return Response({"message": "權限不足"}, status=status.HTTP_403_FORBIDDEN)
        
        worker_id = request.data.get('worker_id')
        schedule_id = request.data.get('schedule_id')
        
        try:
            worker = request.user.company.worker_set.get(id=worker_id)
            schedule = ReminderSchedule.objects.get(id=schedule_id, company=request.user.company)
            
            line_service = LineBotService()
            success = line_service.send_reminder_to_worker(worker, schedule)
            
            if success:
                return Response({"message": "測試提醒發送成功"})
            else:
                return Response({"message": "發送失敗，請檢查勞工是否已綁定 LINE"}, 
                              status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({"message": f"發送失敗：{str(e)}"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)