from rest_framework import serializers
from .models import (
    CustomUser, Company, Worker, FormType, FormSubmission, 
    Experiment, ExperimentFile, LineUserBinding, ReminderSchedule
)

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'code', 'is_super_company']

class UserSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'login_code', 'password', 'role', 'company', 'company_name']
        read_only_fields = ['id']
        extra_kwargs = {'password': {'write_only': True}}  # 確保密碼只寫入不讀出
    
    def get_company_name(self, obj):
        return obj.company.name if obj.company else None
    
    def create(self, validated_data):
        # 從驗證過的數據中取出密碼
        password = validated_data.pop('password', None)
        
        # 創建用戶實例
        user = CustomUser(**validated_data)
        
        # 如果提供了密碼，使用 set_password 方法安全地設置密碼
        if password:
            user.set_password(password)
        
        # 保存用戶
        user.save()
        return user
    
    def update(self, instance, validated_data):
        # 從驗證過的數據中取出密碼
        password = validated_data.pop('password', None)
        
        # 更新其他字段
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 如果提供了密碼，使用 set_password 方法安全地設置密碼
        if password:
            instance.set_password(password)
        
        # 保存用戶
        instance.save()
        return instance

class WorkerSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Worker
        fields = ['id', 'name', 'code', 'company', 'company_name']
    
    def get_company_name(self, obj):
        return obj.company.name if obj.company else None

class FormTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormType
        fields = ['id', 'name', 'description', 'is_required_first_time', 'is_required_subsequent']

class FormSubmissionSerializer(serializers.ModelSerializer):
    form_type_id = serializers.IntegerField(source='form_type.id', read_only=True)
    worker_name = serializers.SerializerMethodField()
    form_type_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = ['id', 'worker', 'worker_name', 'form_type', 'form_type_id', 'form_type_name', 
                 'submission_time', 'submission_count', 'time_segment', 'stage', 'data']
    
    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker else None
    
    def get_form_type_name(self, obj):
        return obj.form_type.name if obj.form_type else None

class ExperimentFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ExperimentFile
        fields = ['id', 'file_field_name', 'original_filename', 'file_url', 'uploaded_at']
    
    def get_file_url(self, obj):
        return obj.get_file_url()

class ExperimentSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()
    experimenter_name = serializers.SerializerMethodField()
    files = ExperimentFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = Experiment
        fields = ['id', 'worker', 'worker_name', 'experimenter', 'experimenter_name',
                 'experiment_time', 'experiment_type', 'data', 'files', 'created_at', 'updated_at']
    
    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker else None
    
    def get_experimenter_name(self, obj):
        return obj.experimenter.username if obj.experimenter else None

# LINE Bot 相關 Serializers
class LineUserBindingSerializer(serializers.ModelSerializer):
    worker_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LineUserBinding
        fields = ['id', 'worker', 'worker_name', 'line_user_id', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_worker_name(self, obj):
        return obj.worker.name if obj.worker else None

class ReminderScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderSchedule
        fields = ['id', 'company', 'name', 'frequency', 'reminder_time', 
                 'reminder_days', 'message_template', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']