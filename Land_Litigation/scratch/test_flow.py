import requests
import re

s = requests.Session()
def debug_flow():
    # 1. Register
    reg_data = {
        "name": "Test Flow",
        "email": "testflow@gmail.com",
        "phone": "9000000001",
        "password": "test",
        "role": "farmer"
    }
    r = s.post("http://127.0.0.1:5000/register_user", data=reg_data, allow_redirects=False)
    print("Reg status:", r.status_code, "Redirect:", r.headers.get("Location"))
    
    # 2. Get OTP (since I cannot see console easily, let me grab current_otp from session or database! Wait, OTP is randomized.
    # Ah, I can't guess the OTP easily unless I read app_log...
