# setup_admin.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 更改為你的設置模組
django.setup()

from api.models import CustomUser, Company

# 創建系統公司
system_company, created = Company.objects.get_or_create(code="0000", defaults={"name": "系統管理"})
print(f"系統管理公司: {system_company.name}, 代碼: {system_company.code}, 新創建: {created}")

# 更新用戶
user = CustomUser.objects.get(username='wei')  # 請確保使用正確的用戶名
user.company = system_company
user.save()
print(f"已將用戶 {user.username} 關聯到公司 {system_company}")