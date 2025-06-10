# check_line_tokens.py
import os
from dotenv import load_dotenv

load_dotenv()

print("=== LINE Bot Token 檢查 ===")

access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_secret = os.getenv('LINE_CHANNEL_SECRET')

if access_token:
    print(f"✅ ACCESS_TOKEN: {access_token[:20]}...{access_token[-10:]} (長度: {len(access_token)})")
else:
    print("❌ ACCESS_TOKEN 未設定")

if channel_secret:
    print(f"✅ CHANNEL_SECRET: {channel_secret[:10]}...{channel_secret[-5:]} (長度: {len(channel_secret)})")
else:
    print("❌ CHANNEL_SECRET 未設定")

# 測試 LINE Bot SDK
try:
    from linebot import LineBotApi, WebhookHandler
    
    if access_token and channel_secret:
        line_bot_api = LineBotApi(access_token)
        handler = WebhookHandler(channel_secret)
        print("✅ LINE Bot SDK 初始化成功")
    else:
        print("❌ Token 或 Secret 缺失")
        
except Exception as e:
    print(f"❌ LINE Bot SDK 初始化失敗: {e}")