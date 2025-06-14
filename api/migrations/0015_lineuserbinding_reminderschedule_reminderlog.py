# Generated by Django 5.1.6 on 2025-05-29 16:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_company_is_super_company_experiment_created_at_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='LineUserBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('line_user_id', models.CharField(max_length=100, unique=True, verbose_name='LINE User ID')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否啟用提醒')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('worker', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='line_binding', to='api.worker')),
            ],
            options={
                'verbose_name': 'LINE用戶綁定',
                'verbose_name_plural': 'LINE用戶綁定',
            },
        ),
        migrations.CreateModel(
            name='ReminderSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='排程名稱')),
                ('frequency', models.CharField(choices=[('daily', '每日'), ('weekly', '每週'), ('monthly', '每月'), ('custom', '自定義')], default='weekly', max_length=20)),
                ('reminder_time', models.TimeField(verbose_name='提醒時間')),
                ('reminder_days', models.JSONField(default=list, help_text='週幾提醒 [1-7]，1為週一')),
                ('message_template', models.TextField(verbose_name='提醒訊息模板')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.company')),
            ],
            options={
                'verbose_name': '提醒排程',
                'verbose_name_plural': '提醒排程',
            },
        ),
        migrations.CreateModel(
            name='ReminderLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message_content', models.TextField(verbose_name='發送內容')),
                ('status', models.CharField(choices=[('sent', '已發送'), ('failed', '發送失敗'), ('clicked', '已點擊'), ('completed', '已完成填寫')], default='sent', max_length=20)),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('clicked_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('worker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.worker')),
                ('schedule', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.reminderschedule')),
            ],
            options={
                'verbose_name': '提醒記錄',
                'verbose_name_plural': '提醒記錄',
            },
        ),
    ]
