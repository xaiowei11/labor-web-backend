from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from django.conf import settings
import json
from .line_bot_handler import LineBotService

@method_decorator(csrf_exempt, name='dispatch')
class LineWebhookView(View):
    def post(self, request):
        print("=== LINE Webhook 收到請求 ===")
        
        # 取得 signature 和 body
        signature = request.META.get('HTTP_X_LINE_SIGNATURE')
        body = request.body.decode('utf-8')
        
        print(f"Signature: {signature}")
        print(f"Body length: {len(body)}")
        print(f"Body preview: {body[:100]}...")
        
        # 檢查是否有必要的資料
        if not signature:
            print("❌ 缺少 X-Line-Signature")
            return HttpResponseBadRequest('Missing signature')
        
        if not body:
            print("❌ 請求 body 為空")
            return HttpResponseBadRequest('Empty body')
        
        try:
            # 初始化 LINE Bot Service
            line_service = LineBotService()
            print("✅ LineBotService 初始化成功")
            
            # 正確的解析方法 - 使用 WebhookHandler 的 parser
            events = line_service.handler.parser.parse(body, signature)
            print(f"✅ 成功解析 {len(events)} 個事件")
            
            # 處理每個事件
            for event in events:
                print(f"處理事件類型: {type(event).__name__}")
                if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
                    print(f"收到文字訊息: '{event.message.text}'")
                    line_service.handle_message(event)
                else:
                    print(f"跳過事件類型: {type(event).__name__}")
            
            print("✅ 所有事件處理完成")
            return HttpResponse('OK')
            
        except InvalidSignatureError as e:
            print(f"❌ 簽名驗證失敗: {e}")
            # 輸出調試信息
            print(f"預期簽名驗證用的 secret: {settings.LINE_CHANNEL_SECRET[:10]}...")
            return HttpResponseBadRequest('Invalid signature')
            
        except Exception as e:
            print(f"❌ 處理錯誤: {e}")
            import traceback
            traceback.print_exc()
            return HttpResponseBadRequest('Processing error')
    
    def get(self, request):
        return HttpResponse('LINE Webhook endpoint is working')