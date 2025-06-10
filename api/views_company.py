# backend/app/views_company.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from .models import Company, CustomUser
from .serializers import CompanySerializer

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])  # 允許未認證的訪問
def public_company_list(request):
    """公開的公司列表API，用於登入頁面顯示公司選項"""
    try:
        # 只返回基本的公司信息（不包含敏感數據）
        companies = Company.objects.all().values('id', 'name', 'code')
        return Response(list(companies))
    except Exception as e:
        return Response(
            {"message": f"獲取公司列表時發生錯誤: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class CompanyListView(APIView):
    """獲取公司列表，僅超級管理員可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        companies = Company.objects.all()
        serializer = CompanySerializer(companies, many=True)
        return Response(serializer.data)

class CompanyCreateView(APIView):
    """創建新公司及其負責人帳號，僅超級管理員可用"""
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        # 獲取公司及負責人資料
        company_data = {
            'name': request.data.get('name'),
            'code': request.data.get('code')
        }
        
        owner_data = {
            'username': request.data.get('owner_username'),
            'login_code': request.data.get('owner_login_code'),
            'password': request.data.get('owner_password'),
            'role': 'owner'
        }
        
        # 驗證數據完整性
        if not all(company_data.values()) or not all(owner_data.values()):
            return Response(
                {"message": "所有欄位都必須填寫"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 檢查公司代碼是否已存在
        if Company.objects.filter(code=company_data['code']).exists():
            return Response(
                {"message": "此公司代碼已存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 檢查使用者名稱和登入代碼是否已存在
        if User.objects.filter(username=owner_data['username']).exists():
            return Response(
                {"message": "此使用者名稱已存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if CustomUser.objects.filter(login_code=owner_data['login_code']).exists():
            return Response(
                {"message": "此登入代碼已存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 創建公司
            company_serializer = CompanySerializer(data=company_data)
            if company_serializer.is_valid():
                company = company_serializer.save()
                
                # 創建公司負責人帳號
                user = CustomUser.objects.create(
                    username=owner_data['username'],
                    login_code=owner_data['login_code'],
                    password=make_password(owner_data['password']),
                    role=owner_data['role'],
                    company=company,
                    is_staff=True  # 可以登入管理後台
                )
                
                return Response(
                    {"message": "公司及負責人帳號創建成功", "company_id": company.id},
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    company_serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {"message": f"創建公司時發生錯誤: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )