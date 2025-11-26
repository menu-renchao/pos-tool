import os
import requests

def get_playwright_server_url():
    # 只读取环境变量 PLAYWRIGHT_SERVER_URL，不提供默认值
    return os.environ.get('PLAYWRIGHT_SERVER_URL')


def get_usable_phone_numbers_remote():
    """通过远程API获取可用手机号列表"""
    try:
        url = get_playwright_server_url()
        resp = requests.get(f"{url}/api/usable_phone_numbers", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("phone_numbers", [])
    except Exception:
        return "服务没生效或者尝试更新手机号列\n移步【设置】->【短信微服务】检查ip和端口是否正确"


def get_latest_code_remote(phone_number, keyword, count):
    """通过远程API获取最新短信内容"""
    try:
        url = get_playwright_server_url()
        payload = {
            "phone_number": phone_number,
            "keyword": keyword,
            "count": count
        }
        resp = requests.post(f"{url}/api/latest_code", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", "")
    except Exception:
        return ""
