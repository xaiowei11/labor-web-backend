# backend/app/urls.py
from django.urls import path
from . import views
from . import views_company
from . import views_worker
from . import views_experiment
from . import views_user
from . import views_form
from .views_line import LineWebhookView
from .views_line_admin import (
    LineBindingListView, 
    ReminderScheduleView, 
    SendTestReminderView
)
from .views_line_api import check_worker_status_api, line_bot_query, test_line_reminder, line_system_status, trigger_smart_reminders, test_specific_worker_reminder


urlpatterns = [
    # 登入相關
    path('api/login/', views.LoginView.as_view(), name='login'),
    
    # 公司管理相關 API
    path('api/companies/', views_company.CompanyListView.as_view(), name='company-list'),
    path('api/companies/create/', views_company.CompanyCreateView.as_view(), name='company-create'),
    path('api/public/companies/', views_company.public_company_list, name='public-company-list'),

    
    # 勞工管理相關 API
    # path('api/companies/<int:company_id>/workers/', views_worker.WorkerListView.as_view(), name='company-workers'),
    path('api/workers/', views_worker.WorkerCreateView.as_view(), name='worker-create'),
    path('api/workers/<int:worker_id>/', views_worker.WorkerDetailView.as_view(), name='worker-detail'),
    path('api/workers/all/', views_worker.WorkerListView.as_view(), name='all-workers'),
    path('api/companies/<int:company_id>/workers/', views_worker.WorkerListView.as_view(), name='company-workers'),
    path('api/public/worker-by-code/', views_worker.WorkerByCodeView.as_view(), name='worker-by-code'),
    path('api/workers/<int:worker_id>/delete/', views_worker.WorkerDetailView.as_view(), name='worker-delete'),
    path('api/workers/<int:worker_id>/force/', views_worker.WorkerForceDeleteView.as_view(), name='worker-force-delete'),


    # path('api/workers/', views_worker.WorkerListView.as_view(), name='all-workers'),


    
    # 表單相關 API
    path('api/form-types/', views_form.FormTypeListView.as_view(), name='form-type-list'),
    path('api/workers/<int:worker_id>/forms/', views_form.get_worker_forms, name='worker-forms'),
    path('api/forms/submit/', views_form.submit_form, name='submit-form'),
    path('api/workers/<int:worker_id>/submissions/', views_form.WorkerSubmissionsView.as_view(), name='worker-submissions'),
    path('api/public/forms/submit/', views_form.submit_form, name='public-submit-form'),
    path('api/public/form-types/', views_form.public_form_types, name='public-form-types'),
    path('api/public/worker-submissions/', views_form.public_worker_submissions, name='public-worker-submissions'),



    # 實驗相關 API
    path('api/experiments/', views_experiment.ExperimentCreateView.as_view(), name='experiment-create'),
    path('api/experiments/<int:experiment_id>/', views_experiment.ExperimentCreateView.as_view(), name='experiment-update'),
    path('api/experimenter/experiments/', views_experiment.ExperimenterExperimentsView.as_view(), name='experimenter-experiments'),
    path('api/companies/experiments/', views_experiment.CompanyExperimentsView.as_view(), name='company-experiments'),
    path('api/workers/<int:worker_id>/experiments/', views_experiment.WorkerExperimentsView.as_view(), name='worker-experiments'),
    
    # 使用者管理相關 API
    path('api/companies/<int:company_id>/users/', views_user.CompanyUsersView.as_view(), name='company-users'),
    path('api/users/', views_user.UserCreateView.as_view(), name='user-create'),
    path('api/users/<int:user_id>/', views_user.UserDetailView.as_view(), name='user-detail'),

    # 超級實驗者相關 API
    path('api/super-experimenter/experiments/', views_experiment.SuperExperimenterView.as_view(), name='super-experimenter-experiments'),
    path('api/super-experimenter/companies/', views_company.CompanyListView.as_view(), name='super-experimenter-companies'),
    path('api/super-experimenter/companies/<int:company_id>/workers/', views_worker.WorkerListView.as_view(), name='super-experimenter-company-workers'),

    # LINE Bot 相關
    path('api/line/webhook/', LineWebhookView.as_view(), name='line-webhook'),
    path('api/line/bindings/', LineBindingListView.as_view(), name='line-bindings'),
    path('api/line/schedules/', ReminderScheduleView.as_view(), name='reminder-schedules'),
    path('api/line/test-reminder/', SendTestReminderView.as_view(), name='test-reminder'),
    path('api/line/worker-status/', check_worker_status_api, name='worker-status-api'),
    path('api/line/query/', line_bot_query, name='line-bot-query'),
    path('api/line/test-reminder/', test_line_reminder, name='test-line-reminder'),
    path('api/line/system-status/', line_system_status, name='line-system-status'),
    path('api/line/trigger-smart-reminders/', trigger_smart_reminders, name='trigger-smart-reminders'),
    path('api/line/test-worker-reminder/', test_specific_worker_reminder, name='test-worker-reminder'),
]