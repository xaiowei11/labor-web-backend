# 在 api/auth_backends.py 文件中
from django.contrib.auth.backends import ModelBackend
from .models import CustomUser, Company

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, login_code=None, company_code=None, password=None, **kwargs):
        print(f"CustomAuthBackend.authenticate 被調用，參數：login_code={login_code}, company_code={company_code}")
        
        try:
            # 先嘗試使用 login_code 和 company_code 找到用戶
            if login_code and company_code:
                try:
                    print(f"嘗試查找公司代碼:{company_code} 和登入代碼:{login_code} 的用戶")
                    user = CustomUser.objects.get(login_code=login_code, company__code=company_code)
                    print(f"找到用戶: {user.username}")
                except CustomUser.DoesNotExist:
                    print(f"找不到符合條件的用戶")
                    return None
                except Exception as e:
                    print(f"查找用戶時出錯: {e}")
                    return None
            
            # 如果沒有 login_code 和 company_code，退回到標準認證
            elif kwargs.get('username'):
                try:
                    print(f"嘗試使用用戶名查找用戶: {kwargs.get('username')}")
                    user = CustomUser.objects.get(username=kwargs.get('username'))
                    print(f"找到用戶: {user.username}")
                except CustomUser.DoesNotExist:
                    print(f"找不到用戶名為 {kwargs.get('username')} 的用戶")
                    return None
                except Exception as e:
                    print(f"查找用戶時出錯: {e}")
                    return None
            else:
                print("未提供登入代碼和公司代碼，也未提供用戶名")
                return None

            # 檢查密碼
            print(f"正在驗證密碼...")
            if user.check_password(password):
                print(f"密碼驗證成功，用戶 {user.username} 認證通過")
                return user
            else:
                print(f"密碼驗證失敗")
                return None
                
        except Exception as e:
            print(f"認證過程中發生未捕獲的錯誤: {e}")
            return None