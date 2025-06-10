# backend/app/views_worker.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import Company, Worker, Experiment, FormSubmission, ExperimentFile  # 新增導入 Experiment 和 FormSubmission
from .serializers import WorkerSerializer

class WorkerListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, company_id=None):
        try:
            # 檢查用戶是否為超級實驗者
            is_super_experimenter = getattr(request.user, 'is_super_experimenter', False)
            
            # 如果是超級實驗者且沒有指定 company_id，返回所有勞工
            if is_super_experimenter and company_id is None:
                workers = Worker.objects.all()
                serializer = WorkerSerializer(workers, many=True)
                return Response(serializer.data)
            
            # 如果沒有提供 company_id，使用用戶的公司
            if company_id is None:
                if is_super_experimenter:
                    # 超級實驗者可以看到所有公司
                    companies = Company.objects.all()
                    data = []
                    for company in companies:
                        workers = Worker.objects.filter(company=company)
                        for worker in workers:
                            data.append({
                                'id': worker.id,
                                'name': worker.name,
                                'code': worker.code,
                                'company': company.id,
                                'company_name': company.name
                            })
                    return Response(data)
                else:
                    company = request.user.company
                    if not company:
                        return Response(
                            {"message": "您沒有關聯到任何公司"},
                            status=status.HTTP_403_FORBIDDEN
                        )
            else:
                company = Company.objects.get(id=company_id)
            
            # 檢查用戶是否有權限訪問該公司
            if request.user.company.id != company.id and request.user.role not in ['superadmin', 'super_experimenter']:
                return Response(
                    {"message": "您沒有權限訪問此公司的勞工"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            workers = Worker.objects.filter(company=company)
            serializer = WorkerSerializer(workers, many=True)
            return Response(serializer.data)
            
        except Company.DoesNotExist:
            return Response(
                {"message": "找不到該公司"},
                status=status.HTTP_404_NOT_FOUND
            )

class WorkerCreateView(APIView):
    """創建新勞工，僅公司管理員可用"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # 檢查用戶是否為公司管理員或老闆
        if request.user.role not in ['owner', 'admin']:
            return Response(
                {"message": "只有公司管理員或老闆可以新增勞工"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 創建勞工
        request.data['company'] = company.id
        serializer = WorkerSerializer(data=request.data)
        
        if serializer.is_valid():
            # 檢查勞工代碼是否已存在於該公司
            if Worker.objects.filter(company=company, code=request.data.get('code')).exists():
                return Response(
                    {"message": "此勞工代碼已存在於您的公司"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            worker = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkerDetailView(APIView):
    """獲取、更新或刪除特定勞工，僅公司管理員可用"""
    
    def get_permissions(self):
        """
        根據請求方法動態設置權限
        GET: 不需要認證（用於表單頁面）
        DELETE: 需要認證（用於刪除操作）
        """
        if self.request.method == 'DELETE':
            return [IsAuthenticated()]
        return []

    def get(self, request, worker_id):
        """獲取特定勞工資訊，用於表單頁面"""
        company_code = request.query_params.get('company_code')
        if not company_code:
            return Response(
                {"message": "缺少必要參數"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 獲取公司
        try:
            company = Company.objects.get(code=company_code)
        except Company.DoesNotExist:
            return Response(
                {"message": "公司代碼不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 獲取勞工
        worker = get_object_or_404(Worker, id=worker_id, company=company)
        serializer = WorkerSerializer(worker)
        return Response(serializer.data)
    
    def delete(self, request, worker_id):
        #"""刪除勞工，僅公司管理員或老闆可用"""
        # 檢查用戶是否為公司管理員或老闆
        if request.user.role not in ['owner', 'admin']:
            return Response(
                {"message": "只有公司管理員或老闆可以刪除勞工"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取勞工
        try:
            worker = Worker.objects.get(id=worker_id, company=company)
        except Worker.DoesNotExist:
            return Response(
                {"message": "找不到該勞工或您沒有權限操作"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 檢查勞工是否有相關的實驗記錄或表單提交記錄
        experiment_count = Experiment.objects.filter(worker=worker).count()
        form_submission_count = FormSubmission.objects.filter(worker=worker).count()
        
        worker_name = worker.name
        
        # 如果有相關資料，先返回400讓前端確認
        if experiment_count > 0 or form_submission_count > 0:
            return Response(
                {"message": "該勞工有相關資料記錄"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 沒有相關資料，直接刪除
        worker.delete()
        return Response(
            {"message": f"勞工 {worker_name} 已成功刪除"},
            status=status.HTTP_200_OK
        )
    
    
class WorkerByCodeView(APIView):
    """通過勞工代碼獲取勞工資訊，不需要認證"""
    permission_classes = [] # 不需要認證
    
    def get(self, request):
        worker_code = request.query_params.get('worker_code')
        company_code = request.query_params.get('company_code')
        
        if not worker_code or not company_code:
            return Response(
                {"message": "缺少必要參數"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 獲取公司
        try:
            company = Company.objects.get(code=company_code)
        except Company.DoesNotExist:
            return Response(
                {"message": "公司代碼不存在"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 獲取勞工
        try:
            worker = Worker.objects.get(code=worker_code, company=company)
            serializer = WorkerSerializer(worker)
            return Response(serializer.data)
        except Worker.DoesNotExist:
            return Response(
                {"message": "找不到該勞工或該勞工不屬於此公司"},
                status=status.HTTP_404_NOT_FOUND
            )


class WorkerForceDeleteView(APIView):
    """強制刪除勞工及其所有相關資料"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, worker_id):
        # 檢查用戶是否為公司管理員或老闆
        if request.user.role not in ['owner', 'admin']:
            return Response(
                {"message": "只有公司管理員或老闆可以刪除勞工"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取勞工
        try:
            worker = Worker.objects.get(id=worker_id, company=company)
        except Worker.DoesNotExist:
            return Response(
                {"message": "找不到該勞工或您沒有權限操作"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        worker_name = worker.name
        
        # 強制刪除：刪除所有相關資料
        try:
            with transaction.atomic():
                # 刪除實驗檔案記錄（實際檔案也會被刪除）
                experiment_files = ExperimentFile.objects.filter(experiment__worker=worker)
                for exp_file in experiment_files:
                    if exp_file.file:
                        try:
                            exp_file.file.delete()  # 刪除實際檔案
                        except:
                            pass  # 如果檔案不存在，忽略錯誤
                
                # 刪除實驗記錄（這會連帶刪除實驗檔案記錄）
                Experiment.objects.filter(worker=worker).delete()
                
                # 刪除表單提交記錄
                FormSubmission.objects.filter(worker=worker).delete()
                
                # 最後刪除勞工
                worker.delete()
                
            return Response(
                {"message": f"勞工 {worker_name} 及其所有相關資料已成功刪除"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"message": f"刪除時發生錯誤: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )