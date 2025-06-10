from django.shortcuts import render
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Company, CustomUser
from .serializers import UserSerializer, FormTypeSerializer
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from django.utils import timezone 

# views.py
@api_view(['GET'])
def get_worker_forms(request, worker_id):
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
def submit_form(request):
    worker_id = request.data.get('worker_id')
    form_type_id = request.data.get('form_type_id')
    form_data = request.data.get('form_data')
    
    worker = Worker.objects.get(id=worker_id)
    
    # 檢查是否可以提交表單
    last_submission = FormSubmission.objects.filter(
        worker=worker,
        form_type_id=form_type_id
    ).order_by('-submission_time').first()
    
    if last_submission and timezone.now() < last_submission.submission_time + timezone.timedelta(hours=1):
        return Response({
            'error': '請等到下一個小時後再提交表單',
            'next_available': last_submission.submission_time + timezone.timedelta(hours=1)
        }, status=400)
    
    # 計算此次是第幾次提交
    submission_count = FormSubmission.objects.filter(worker=worker).count() // 4 + 1
    if last_submission:
        submission_count = last_submission.submission_count + 1
    
    # 創建新的提交記錄
    submission = FormSubmission.objects.create(
        worker=worker,
        form_type_id=form_type_id,
        submission_count=submission_count,
        data=form_data
    )
    
    return Response({'success': True, 'submission_id': submission.id})

class LoginView(APIView):

    permission_classes = [AllowAny]


    def post(self, request):
        company_code = request.data.get('company_code')
        login_code = request.data.get('login_code')
        password = request.data.get('password')
        
        # 檢查參數是否完整
        if not all([company_code, login_code, password]):
            return Response(
                {"message": "公司代碼、登入帳號和密碼都必須提供"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 檢查公司代碼是否存在
            company = Company.objects.get(code=company_code)
        except Company.DoesNotExist:
            return Response(
                {"message": "公司代碼不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # 從登入帳號找到用戶
            user = CustomUser.objects.get(login_code=login_code, company=company)
        except CustomUser.DoesNotExist:
            return Response(
                {"message": "登入帳號不存在或不屬於此公司"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 驗證密碼
        user_auth = authenticate(
            request=request,
            login_code=login_code,
            company_code=company_code,
            password=password
        )
        if not user_auth:
            return Response(
                {"message": "密碼錯誤"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 生成或取得 token
        token, created = Token.objects.get_or_create(user=user)
        
        # 返回用戶信息和 token
        return Response({
            "token": token.key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)