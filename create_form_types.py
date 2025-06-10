"""
表單類型創建腳本
用途：設置正確的表單類型ID與前端映射一致
使用方法：python manage.py shell < create_form_types.py
"""

import os
import django

# 確保Django環境已設置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 可能需要修改為您的項目設置
django.setup()

# 導入必要的模型
from api.models import FormType  # 修改為您實際的應用和模型名稱
from django.db import transaction

# 顯示操作開始
print("\n=== 開始設置表單類型 ===\n")

# 檢查現有的表單類型
print("目前存在的表單類型:")
for form in FormType.objects.all().order_by('id'):
    print(f"ID: {form.id}, 名稱: {form.name}")

# 定義要創建的表單類型
form_types = [
    {
        'id': 1,
        'name': '睡眠時數調查',
        'description': '記錄睡眠時間',
        'is_required_first_time': True,
        'is_required_subsequent': True,
    },
    {
        'id': 2,
        'name': '嗜睡量表',
        'description': '評估當前嗜睡程度',
        'is_required_first_time': True,
        'is_required_subsequent': True,
    },
    {
        'id': 3,
        'name': '視覺疲勞量表',
        'description': '評估眼睛健康狀況',
        'is_required_first_time': True,
        'is_required_subsequent': True,
    },
    {
        'id': 4,
        'name': 'NASA-TLX工作負荷量表',
        'description': '評估工作負荷程度',
        'is_required_first_time': True,
        'is_required_subsequent': True,
    },
]

# 使用事務確保數據一致性
with transaction.atomic():
    print("\n開始更新/創建表單類型...")
    
    for form_data in form_types:
        form_id = form_data['id']
        form_name = form_data['name']
        
        try:
            # 嘗試獲取現有表單
            existing_form = FormType.objects.get(id=form_id)
            
            # 更新現有表單
            for key, value in form_data.items():
                setattr(existing_form, key, value)
            existing_form.save()
            print(f"✓ 已更新 ID={form_id} 的表單: {form_name}")
            
        except FormType.DoesNotExist:
            # 創建新表單
            FormType.objects.create(**form_data)
            print(f"+ 已創建 ID={form_id} 的表單: {form_name}")

# 驗證結果
print("\n最終表單類型列表:")
for form in FormType.objects.all().order_by('id'):
    print(f"ID: {form.id}, 名稱: {form.name}, 描述: {form.description[:30]}...")

print("\n=== 表單類型設置完成 ===\n")