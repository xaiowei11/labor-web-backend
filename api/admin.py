from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError

from .models import Company, CustomUser, Worker, FormType, FormSubmission, Experiment, ExperimentFile

# 公司創建表單
class CompanyCreationForm(forms.ModelForm):
    name = forms.CharField(label="公司名稱", widget=forms.TextInput)
    code = forms.CharField(label="公司代碼", widget=forms.TextInput)
    is_super_company = forms.BooleanField(label="是否為超級實驗公司", required=False)
    owner_username = forms.CharField(label="公司老闆帳號", widget=forms.TextInput)
    owner_password1 = forms.CharField(label="公司老闆密碼", widget=forms.PasswordInput)
    owner_password2 = forms.CharField(label="確認密碼", widget=forms.PasswordInput)
    owner_fullname = forms.CharField(label="老闆姓名", widget=forms.TextInput)
    owner_login_code = forms.CharField(label="老闆登入代碼", widget=forms.TextInput)

    class Meta:
        model = Company
        fields = ('name', 'code', 'is_super_company')

    def clean_owner_username(self):
        username = self.cleaned_data.get('owner_username')
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError("該用戶名已存在")
        return username

    def clean_owner_login_code(self):
        login_code = self.cleaned_data.get('owner_login_code')
        if CustomUser.objects.filter(login_code=login_code).exists():
            raise ValidationError("該登入代碼已存在")
        return login_code

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Company.objects.filter(code=code).exists():
            raise ValidationError("該公司代碼已存在")
        return code

    def clean_owner_password2(self):
        password1 = self.cleaned_data.get("owner_password1")
        password2 = self.cleaned_data.get("owner_password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("兩次輸入的密碼不一致")
        return password2

    def save(self, commit=True):
        company = super().save(commit=False)
        if commit:
            company.save()
            
            # 創建公司老闆帳號
            owner = CustomUser(
                username=self.cleaned_data['owner_username'],
                full_name=self.cleaned_data['owner_fullname'],
                login_code=self.cleaned_data['owner_login_code'],
                company=company,
                role='owner',
                is_staff=True
            )
            owner.set_password(self.cleaned_data['owner_password1'])
            owner.save()
            
        return company

# 公司管理界面
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_super_company']
    search_fields = ['name', 'code']
    list_filter = ['is_super_company']
    ordering = ['name']
    
    def get_form(self, request, obj=None, **kwargs):
        """
        使用自定義表單進行公司創建
        """
        if obj is None:  # 添加新公司時
            return CompanyCreationForm
        return super().get_form(request, obj, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """
        重寫保存方法，確保公司老闆一起創建
        """
        if not change:  # 新建公司
            # 通過表單.save()方法保存，這會調用表單內定義的創建老闆代碼
            form.save()
        else:
            super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        # 只有超級管理員和超級用戶可以添加公司
        return request.user.is_superuser or getattr(request.user, 'role', None) == 'superadmin'

# 自定義用戶管理界面
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'full_name', 'login_code', 'role', 'company', 'is_staff']
    list_filter = ['role', 'company', 'is_staff', 'is_superuser']
    fieldsets = UserAdmin.fieldsets + (
        ('自定義信息', {'fields': ('login_code', 'role', 'company', 'full_name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('自定義信息', {'fields': ('login_code', 'role', 'company', 'full_name')}),
    )
    search_fields = ['username', 'email', 'login_code', 'full_name']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('company')

admin.site.register(CustomUser, CustomUserAdmin)

# 勞工管理界面
@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company']
    list_filter = ['company']
    search_fields = ['name', 'code', 'company__name']
    ordering = ['company', 'name']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('company')

# 表單類型管理界面
@admin.register(FormType)
class FormTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_required_first_time', 'is_required_subsequent']
    list_filter = ['is_required_first_time', 'is_required_subsequent']
    search_fields = ['name', 'description']
    ordering = ['name']

# 表單提交管理界面
@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['worker', 'form_type', 'submission_time', 'submission_count', 'time_segment', 'stage']
    list_filter = ['form_type', 'worker__company', 'submission_time', 'stage', 'time_segment']
    search_fields = ['worker__name', 'worker__code', 'form_type__name']
    date_hierarchy = 'submission_time'
    ordering = ['-submission_time']
    readonly_fields = ['submission_time']
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('worker', 'form_type', 'worker__company')

# 實驗檔案內聯管理
class ExperimentFileInline(admin.TabularInline):
    model = ExperimentFile
    extra = 0
    readonly_fields = ['uploaded_at', 'original_filename', 'get_file_url']
    fields = ['file_field_name', 'file', 'original_filename', 'get_file_url', 'uploaded_at']
    
    def get_file_url(self, obj):
        if obj.file:
            return f'<a href="{obj.file.url}" target="_blank">下載檔案</a>'
        return '-'
    get_file_url.allow_tags = True
    get_file_url.short_description = '檔案連結'

# 實驗管理界面
@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ['worker', 'experimenter', 'experiment_type', 'experiment_time', 'created_at']
    list_filter = ['experiment_type', 'worker__company', 'experimenter', 'experiment_time', 'created_at']
    search_fields = ['worker__name', 'worker__code', 'experimenter__username']
    date_hierarchy = 'experiment_time'
    ordering = ['-experiment_time']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ExperimentFileInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('worker', 'experimenter', 'experiment_type', 'experiment_time')
        }),
        ('實驗數據', {
            'fields': ('data',),
            'classes': ['collapse']
        }),
        ('系統資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('worker', 'experimenter', 'worker__company')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "worker":
            # 根據用戶權限過濾勞工選項
            if not request.user.is_superuser:
                if hasattr(request.user, 'company') and request.user.company:
                    kwargs["queryset"] = Worker.objects.filter(company=request.user.company)
        elif db_field.name == "experimenter":
            # 限制實驗者選項
            kwargs["queryset"] = CustomUser.objects.filter(role__in=['experimenter', 'super_experimenter'])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# 實驗檔案管理界面
@admin.register(ExperimentFile)
class ExperimentFileAdmin(admin.ModelAdmin):
    list_display = ['experiment', 'file_field_name', 'original_filename', 'uploaded_at', 'get_file_size']
    list_filter = ['experiment__experiment_type', 'uploaded_at', 'file_field_name']
    search_fields = ['experiment__worker__name', 'original_filename', 'file_field_name']
    readonly_fields = ['uploaded_at', 'get_file_size', 'get_file_url']
    ordering = ['-uploaded_at']
    
    fieldsets = (
        ('檔案資訊', {
            'fields': ('experiment', 'file_field_name', 'original_filename')
        }),
        ('檔案內容', {
            'fields': ('file', 'get_file_url', 'get_file_size')
        }),
        ('系統資訊', {
            'fields': ('uploaded_at',),
            'classes': ['collapse']
        }),
    )
    
    def get_file_size(self, obj):
        if obj.file:
            size = obj.file.size
            if size < 1024:
                return f'{size} B'
            elif size < 1024 * 1024:
                return f'{size / 1024:.1f} KB'
            else:
                return f'{size / (1024 * 1024):.1f} MB'
        return '-'
    get_file_size.short_description = '檔案大小'
    
    def get_file_url(self, obj):
        if obj.file:
            return f'<a href="{obj.file.url}" target="_blank">下載檔案</a>'
        return '-'
    get_file_url.allow_tags = True
    get_file_url.short_description = '檔案連結'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('experiment', 'experiment__worker', 'experiment__experimenter')

# 自定義管理界面標題
admin.site.site_header = '勞工健康數據平台管理系統'
admin.site.site_title = '勞工健康數據平台'
admin.site.index_title = '歡迎使用勞工健康數據平台管理系統'