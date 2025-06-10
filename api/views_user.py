# backend/app/views_user.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from .models import Company
from .serializers import UserSerializer

User = get_user_model()

class CompanyUsersView(APIView):
    """獲取公司所有使用者，僅公司老闆可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, company_id):
        # 檢查用戶是否有權限查看
        if request.user.role != 'owner' and request.user.company.id != company_id:
            return Response(
                {"message": "您沒有權限查看此公司的使用者"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {"message": "找不到該公司"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 獲取該公司所有使用者
        users = User.objects.filter(company=company)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class UserCreateView(APIView):
    """創建新使用者，僅公司老闆可用"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):

        print("後端接收到的用戶數據:", request.data)

        if 'password' not in request.data:
            return Response(
                {"message": "缺少密碼字段"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 檢查用戶是否為公司老闆
        if request.user.role != 'owner':
            return Response(
                {"message": "只有公司負責人可以新增使用者"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 檢查使用者名稱和登入代碼是否已存在
        username = request.data.get('username')
        login_code = request.data.get('login_code')
        
        if User.objects.filter(username=username).exists():
            return Response(
                {"message": "此使用者名稱已存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(login_code=login_code).exists():
            return Response(
                {"message": "此登入代碼已存在"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 創建使用者
        try:
            user_data = {
                'username': username,
                'login_code': login_code,
                'password': make_password(request.data.get('password')),
                'role': request.data.get('role'),
                'company': company.id,
                'is_staff': True if request.data.get('role') == 'admin' else False
            }
            
            serializer = UserSerializer(data=user_data)
            if serializer.is_valid():
                user = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    serializer.errors,
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            return Response(
                {"message": f"創建使用者時發生錯誤: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UserDetailView(APIView):
    """獲取、更新或刪除特定使用者，僅公司老闆可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        # 檢查用戶是否有權限操作
        if request.user.role != 'owner':
            return Response(
                {"message": "只有公司負責人可以查看使用者詳情"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取使用者
        try:
            user = User.objects.get(id=user_id, company=request.user.company)
        except User.DoesNotExist:
            return Response(
                {"message": "找不到該使用者或您沒有權限查看"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    def delete(self, request, user_id):
        # 檢查用戶是否有權限操作
        if request.user.role != 'owner':
            return Response(
                {"message": "只有公司負責人可以刪除使用者"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取使用者
        try:
            user = User.objects.get(id=user_id, company=request.user.company)
        except User.DoesNotExist:
            return Response(
                {"message": "找不到該使用者或您沒有權限操作"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 不能刪除公司負責人
        if user.role == 'owner':
            return Response(
                {"message": "不能刪除公司負責人帳號"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 刪除使用者
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def patch(self, request, user_id):
        # 檢查用戶是否有權限操作
        if request.user.role != 'owner':
            return Response(
                {"message": "只有公司負責人可以更新使用者"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取使用者
        try:
            user = User.objects.get(id=user_id, company=request.user.company)
        except User.DoesNotExist:
            return Response(
                {"message": "找不到該使用者或您沒有權限操作"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 更新使用者資料
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)