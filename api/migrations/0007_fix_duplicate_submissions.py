from django.db import migrations

def fix_duplicates(apps, schema_editor):
    FormSubmission = apps.get_model('api', 'FormSubmission')
    
    # 獲取所有表單提交
    all_submissions = FormSubmission.objects.all()
    
    # 用於跟踪已處理的組合
    processed_combinations = set()
    
    # 用於存儲需要保留的記錄ID
    to_keep = set()
    
    # 查找重複項並只保留最新的
    for submission in all_submissions:
        # 創建組合鍵
        combo_key = (
            submission.worker_id, 
            submission.form_type_id, 
            submission.submission_count, 
            submission.time_segment
        )
        
        # 如果這個組合已經處理過，繼續下一個
        if combo_key in processed_combinations:
            continue
            
        # 獲取所有匹配的提交
        matching_submissions = FormSubmission.objects.filter(
            worker_id=submission.worker_id,
            form_type_id=submission.form_type_id,
            submission_count=submission.submission_count,
            time_segment=submission.time_segment
        ).order_by('-submission_time')  # 按提交時間降序排序
        
        # 如果有多個匹配項
        if matching_submissions.count() > 1:
            # 只保留最新的
            to_keep.add(matching_submissions[0].id)
            
            # 輸出調試信息
            print(f"處理重複項: {combo_key}, 保留ID: {matching_submissions[0].id}, 刪除數量: {matching_submissions.count()-1}")
        else:
            # 如果只有一個，也添加到保留集
            to_keep.add(matching_submissions[0].id)
        
        # 標記這個組合已處理
        processed_combinations.add(combo_key)
    
    # 刪除不在保留集中的記錄
    for submission in all_submissions:
        if submission.id not in to_keep:
            submission.delete()
            print(f"刪除重複記錄 ID: {submission.id}")

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_formsubmission_time_segment_and_more'),  # 替換為前一個遷移的名稱
    ]

    operations = [
        migrations.RunPython(fix_duplicates),
    ]