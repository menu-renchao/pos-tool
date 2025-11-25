import requests

PLAYWRIGHT_SERVER_URL = "http://192.168.0.17:8000"  # 可根据实际情况修改

def get_usable_phone_numbers_remote():
    """通过远程API获取可用手机号列表"""
    try:
        resp = requests.get(f"{PLAYWRIGHT_SERVER_URL}/api/usable_phone_numbers", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("phone_numbers", [])
    except Exception as e:
        return "服务没生效"


def get_latest_code_remote(phone_number, keyword, count):
    """通过远程API获取最新短信内容"""
    try:
        payload = {
            "phone_number": phone_number,
            "keyword": keyword,
            "count": count
        }
        resp = requests.post(f"{PLAYWRIGHT_SERVER_URL}/api/latest_code", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", "")
    except Exception as e:
        return ""

