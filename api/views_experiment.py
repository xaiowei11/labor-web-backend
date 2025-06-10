# backend/app/views_experiment.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.core.files.storage import default_storage
import json
from .models import Experiment, Worker, ExperimentFile, Company
from .serializers import ExperimentSerializer

class ExperimenterExperimentsView(APIView):
    """獲取實驗者自己的實驗記錄"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 檢查用戶是否為實驗者或超級實驗者
        if request.user.role not in ['experimenter', 'super_experimenter']:
            return Response(
                {"message": "只有實驗者可以訪問此資源"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取該實驗者的所有實驗記錄
        experiments = Experiment.objects.filter(experimenter=request.user).order_by('-experiment_time')
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)

class ExperimentCreateView(APIView):
    """創建新實驗記錄，支援檔案上傳"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def post(self, request):
        # 檢查用戶是否為實驗者或超級實驗者
        if request.user.role not in ['experimenter', 'super_experimenter']:
            return Response(
                {"message": "只有實驗者可以創建實驗記錄"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 檢查用戶是否來自超級實驗公司
        is_from_super_company = (request.user.company and 
                               getattr(request.user.company, 'is_super_company', False)) or \
                              request.user.role == 'super_experimenter'
        
        # 檢查勞工是否存在
        worker_id = request.data.get('worker')
        try:
            if is_from_super_company:
                # 超級實驗公司的用戶可以為任何勞工創建實驗
                worker = Worker.objects.get(id=worker_id)
            else:
                # 普通公司的用戶只能為自己公司的勞工創建實驗
                worker = Worker.objects.get(id=worker_id, company=request.user.company)
        except Worker.DoesNotExist:
            return Response(
                {"message": "找不到該勞工或您沒有權限操作該勞工"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 處理實驗數據
        experiment_data = {
            'worker': worker.id,
            'experimenter': request.user.id,
            'experiment_time': request.data.get('experiment_time'),
            'experiment_type': request.data.get('experiment_type'),
        }
        
        # 處理 data 欄位 - 可能是 JSON 字符串或直接的數據
        data_field = request.data.get('data')
        if isinstance(data_field, str):
            try:
                experiment_data['data'] = json.loads(data_field)
            except json.JSONDecodeError:
                experiment_data['data'] = {}
        else:
            experiment_data['data'] = data_field or {}
        
        # 創建實驗記錄
        serializer = ExperimentSerializer(data=experiment_data)
        if serializer.is_valid():
            experiment = serializer.save()
            
            # 處理檔案上傳
            uploaded_files = []
            for key, file in request.FILES.items():
                if key.startswith('file_'):
                    # 提取原始欄位名稱 (移除 'file_' 前綴)
                    field_name = key[5:]  # 移除 'file_' 前綴
                    
                    # 創建實驗檔案記錄
                    experiment_file = ExperimentFile.objects.create(
                        experiment=experiment,
                        file_field_name=field_name,
                        file=file,
                        original_filename=file.name
                    )
                    uploaded_files.append(experiment_file)
                    
                    # 將檔案 URL 添加到實驗數據中
                    if not experiment.data:
                        experiment.data = {}
                    experiment.data[field_name] = experiment_file.get_file_url()
            
            # 如果有檔案上傳，更新實驗記錄
            if uploaded_files:
                experiment.save()
            
            # 重新序列化以包含檔案信息
            response_serializer = ExperimentSerializer(experiment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, experiment_id=None):
        """更新實驗記錄，支援逐步填寫"""
        # 檢查用戶是否為實驗者或超級實驗者
        if request.user.role not in ['experimenter', 'super_experimenter']:
            return Response(
                {"message": "只有實驗者可以更新實驗記錄"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取實驗記錄
        try:
            experiment = Experiment.objects.get(id=experiment_id)
        except Experiment.DoesNotExist:
            return Response(
                {"message": "找不到該實驗記錄"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 檢查用戶是否來自超級實驗公司
        is_from_super_company = (request.user.company and 
                               getattr(request.user.company, 'is_super_company', False)) or \
                              request.user.role == 'super_experimenter'
        
        # 修改權限檢查邏輯：檢查是否有權限操作該勞工
        if is_from_super_company:
            # 超級實驗公司/超級實驗者可以更新任何實驗記錄
            pass
        else:
            # 普通公司的實驗者只能更新自己公司勞工的實驗記錄
            if not request.user.company:
                return Response(
                    {"message": "您沒有關聯到任何公司"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if experiment.worker.company != request.user.company:
                return Response(
                    {"message": "您只能更新自己公司勞工的實驗記錄"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # 更新實驗數據
        if 'data' in request.data:
            updated_data = request.data['data']
            # 合併現有數據和新數據
            if experiment.data:
                experiment.data.update(updated_data)
            else:
                experiment.data = updated_data
            
            # 更新 experimenter 為當前用戶（記錄最後更新者）
            experiment.experimenter = request.user
            experiment.save()
        
        # 重新序列化返回更新後的數據
        serializer = ExperimentSerializer(experiment)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompanyExperimentsView(APIView):
    """獲取公司所有的實驗記錄，公司管理員和老闆可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 檢查用戶是否為公司管理員或老闆
        if request.user.role not in ['owner', 'admin']:
            return Response(
                {"message": "只有公司管理員或老闆可以查看公司所有實驗記錄"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取公司
        company = request.user.company
        if not company:
            return Response(
                {"message": "您沒有關聯到任何公司"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取該公司所有勞工的實驗記錄
        workers = Worker.objects.filter(company=company).values_list('id', flat=True)
        experiments = Experiment.objects.filter(worker__in=workers).order_by('-experiment_time')
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)

class WorkerExperimentsView(APIView):
    """獲取特定勞工的實驗記錄，公司管理員和實驗者可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, worker_id):
        # 檢查用戶角色
        if request.user.role not in ['owner', 'admin', 'experimenter', 'super_experimenter', 'superadmin']:
            return Response(
                {"message": "您沒有權限查看此資源"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 檢查用戶是否來自超級實驗公司
        is_from_super_company = (request.user.company and 
                               getattr(request.user.company, 'is_super_company', False)) or \
                              request.user.role in ['super_experimenter', 'superadmin']
        
        # 獲取勞工
        try:
            # 超級實驗公司的用戶可以訪問任何勞工的實驗
            if is_from_super_company:
                worker = Worker.objects.get(id=worker_id)
            else:
                # 普通公司的用戶只能訪問自己公司的勞工
                company = request.user.company
                if not company:
                    return Response(
                        {"message": "您沒有關聯到任何公司"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                
                worker = Worker.objects.get(id=worker_id, company=company)
                
        except Worker.DoesNotExist:
            return Response(
                {"message": "找不到該勞工或您沒有權限查看該勞工"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 獲取該勞工的所有實驗記錄
        experiments = Experiment.objects.filter(worker=worker).order_by('-experiment_time')
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)

class SuperExperimenterView(APIView):
    """獲取所有公司的實驗記錄，僅超級實驗者可用"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 檢查用戶是否為超級實驗者或超級管理員
        if request.user.role not in ['super_experimenter', 'superadmin']:
            return Response(
                {"message": "只有超級實驗者可以訪問此資源"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 獲取所有實驗記錄
        experiments = Experiment.objects.all().order_by('-experiment_time')
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)