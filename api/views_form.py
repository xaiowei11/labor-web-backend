# backend/app/views_form.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import FormType, FormSubmission, Worker, Company
from .serializers import FormTypeSerializer, FormSubmissionSerializer
from rest_framework.permissions import AllowAny


class FormTypeListView(APIView):
    """獲取所有表單類型"""
    
    def get(self, request):
        form_types = FormType.objects.all()
        serializer = FormTypeSerializer(form_types, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def get_worker_forms(request, worker_id):
    """獲取勞工應填寫的表單類型"""
    try:
        worker = Worker.objects.get(id=worker_id)
        
        # 計算該勞工已填寫的次數
        submission_count = FormSubmission.objects.filter(
            worker=worker
        ).values('submission_count').order_by('-submission_count').first()
        
        current_count = 0 if submission_count is None else submission_count['submission_count']
        
        # 根據填寫次數決定應顯示哪些表單
        if current_count == 0:
            # 首次填寫，顯示所有表單
            forms_to_show = FormType.objects.filter(is_required_first_time=True)
        else:
            # 後續填寫，只顯示部分表單
            forms_to_show = FormType.objects.filter(is_required_subsequent=True)
        
        return Response({
            'submissionCount': current_count,
            'formsToShow': FormTypeSerializer(forms_to_show, many=True).data
        })
    except Worker.DoesNotExist:
        return Response({'error': '找不到該勞工'}, status=404)

@api_view(['POST'])
@permission_classes([AllowAny])  
def submit_form(request):
    """提交表單數據"""
    worker_id = request.data.get('worker_id')
    form_type_id = request.data.get('form_type_id')
    form_data = request.data.get('form_data')
    submission_count = request.data.get('submission_count', 1)
    time_segment = int(request.data.get('time_segment', 1))
    stage = request.data.get('stage', 0)  # 新增對階段參數的處理
    
    if not all([worker_id, form_type_id, form_data]):
        return Response({'error': '缺少必要參數'}, status=400)
    
    try:
        worker = Worker.objects.get(id=worker_id)
        form_type = FormType.objects.get(id=form_type_id)
    except Worker.DoesNotExist:
        return Response({'error': '找不到該勞工'}, status=404)
    except FormType.DoesNotExist:
        return Response({'error': '找不到該表單類型'}, status=404)
    
    # 檢查是否已存在相同的提交記錄
    existing_submission = FormSubmission.objects.filter(
        worker=worker,
        form_type=form_type,
        submission_count=submission_count,
        time_segment=time_segment,
        stage=stage  # 新增階段條件
    ).first()
    
    if existing_submission:
        # 找出當前最大的時段數字
        max_segment = FormSubmission.objects.filter(
            worker=worker,
            form_type=form_type,
            submission_count=submission_count,
            stage=stage  # 新增階段條件
        ).order_by('-time_segment').values_list('time_segment', flat=True).first() or 0
        
        # 使用下一個時段數字
        time_segment = max_segment + 1
    
    # 創建新的提交記錄
    submission = FormSubmission.objects.create(
        worker=worker,
        form_type=form_type,
        submission_count=submission_count,
        time_segment=time_segment,
        stage=stage,  # 新增階段字段
        data=form_data
    )
    
    return Response({
        'success': True, 
        'submission_id': submission.id,
        'submission_count': submission_count,
        'time_segment': time_segment,
        'stage': stage  # 返回階段信息
    })

class WorkerSubmissionsView(APIView):
    """獲取勞工所有表單提交記錄，需要認證"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, worker_id):
        # 檢查用戶是否有權限查看
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取勞工
        worker = get_object_or_404(Worker, id=worker_id, company=company)
        
        # 獲取所有提交記錄
        submissions = FormSubmission.objects.filter(worker=worker).order_by('-submission_time')
        serializer = FormSubmissionSerializer(submissions, many=True)
        
        return Response(serializer.data)
    

@api_view(['GET'])
@permission_classes([AllowAny])
def public_form_types(request):
    """公開獲取所有表單類型"""
    form_types = FormType.objects.all()
    serializer = FormTypeSerializer(form_types, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_worker_submissions(request):
    """公開獲取勞工的表單提交記錄"""
    worker_code = request.query_params.get('worker_code')
    company_code = request.query_params.get('company_code')
    
    if not worker_code or not company_code:
        return Response({'error': '缺少必要參數'}, status=400)
    
    try:
        company = Company.objects.get(code=company_code)
        worker = Worker.objects.get(code=worker_code, company=company)
        
        # 獲取所有提交記錄
        submissions = FormSubmission.objects.filter(worker=worker).order_by('-submission_time')
        
        # 格式化為前端需要的結構
        result = []
        for sub in submissions:
            result.append({
                'id': sub.id,
                'worker_id': sub.worker.id,
                'form_type_id': sub.form_type.id,
                'submission_count': sub.submission_count,
                'time_segment': sub.time_segment,
                'stage': sub.stage,  # 新增返回階段信息
                'submission_time': sub.submission_time.isoformat()
            })
        
        return Response(result)
        
    except Company.DoesNotExist:
        return Response({'error': '找不到該公司'}, status=404)
    except Worker.DoesNotExist:
        return Response({'error': '找不到該勞工'}, status=404)