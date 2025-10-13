import socket
import ipaddress
import concurrent.futures
import requests
import json
from datetime import datetime
from typing import List, Dict, Optional


def scan_port(ip, port, timeout=1):
    """扫描指定IP的指定端口是否开放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((str(ip), port))
            if result == 0:
                return ip
    except:
        return None
    return None


def get_local_network():
    """获取本地网络地址和掩码"""
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return ipaddress.IPv4Network(f"{local_ip}/24", strict=False)


def fetch_company_profile(ip, port=22080, timeout=3):
    """调用API接口获取公司信息"""
    url = f"http://{ip}:{port}/kpos/webapp/store/fetchCompanyProfile"

    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析错误: {str(e)}"}


def extract_required_info(api_response):
    """从API响应中提取所需信息"""
    if "error" in api_response:
        return {"error": api_response["error"]}

    try:
        # 提取所需字段
        result = {
            "merchantId": api_response.get("company", {}).get("merchantId"),
            "name": api_response.get("company", {}).get("name"),
            "version": api_response.get("company", {}).get("appInfo", {}).get("version")
        }

        # 检查是否成功获取到必要信息
        if not any(result.values()):
            return {"error": "响应中未找到所需字段"}

        return result
    except Exception as e:
        return {"error": f"数据提取错误: {str(e)}"}


def scan_and_fetch_company_info(port=22080):
    """扫描局域网并获取公司信息"""
    network = get_local_network()
    results = []

    print(f"开始扫描局域网 {network} 中开放端口 {port} 的服务...")
    print("=" * 60)

    # 第一阶段：扫描开放端口的IP
    open_ips = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(scan_port, ip, port): ip for ip in network.hosts()}

        for future in concurrent.futures.as_completed(futures):
            ip = futures[future]
            try:
                result = future.result()
                if result:
                    open_ips.append(str(result))
                    print(f"✓ 发现开放端口 {port} 的IP: {result}")
            except Exception as e:
                print(f"✗ 扫描 {ip} 时出错: {e}")

    print(f"\n发现 {len(open_ips)} 个开放端口 {port} 的设备")
    print("开始获取公司信息...")
    print("=" * 60)

    # 第二阶段：调用API获取信息
    for ip in open_ips:
        print(f"\n正在查询 {ip}...")

        # 获取API响应
        api_response = fetch_company_profile(ip, port)

        if "error" in api_response:
            result = {
                "ip": ip,
                "status": "error",
                "error": api_response["error"]
            }
            print(f"✗ {ip} - 错误: {api_response['error']}")
        else:
            # 提取所需信息
            extracted_info = extract_required_info(api_response)

            if "error" in extracted_info:
                result = {
                    "ip": ip,
                    "status": "error",
                    "error": extracted_info["error"]
                }
                print(f"✗ {ip} - 数据提取错误: {extracted_info['error']}")
            else:
                result = {
                    "ip": ip,
                    "status": "success",
                    "merchantId": extracted_info["merchantId"],
                    "name": extracted_info["name"],
                    "version": extracted_info["version"]
                }
                print(f"✓ {ip} - 成功获取信息")
                print(f"  商家ID: {extracted_info['merchantId']}")
                print(f"  名称: {extracted_info['name']}")
                print(f"  版本: {extracted_info['version']}")

        results.append(result)

    return results


def save_results_to_file(results, filename="scan_results.json"):
    """将结果保存到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存到: {filename}")


def print_summary(results):
    """打印扫描结果摘要"""
    print("\n" + "=" * 60)
    print("扫描结果摘要")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    print(f"成功获取信息: {success_count} 个设备")
    print(f"获取失败: {error_count} 个设备")

    if success_count > 0:
        print("\n成功获取信息的设备详情:")
        print("-" * 40)
        for result in results:
            if result["status"] == "success":
                print(f"IP: {result['ip']}")
                print(f"  商家ID: {result['merchantId']}")
                print(f"  名称: {result['name']}")
                print(f"  版本: {result['version']}")
                print()


if __name__ == "__main__":
    start_time = datetime.now()

    try:
        target_port = 22080
        results = scan_and_fetch_company_info(target_port)

        # 保存结果到文件
        save_results_to_file(results)

        # 打印摘要
        print_summary(results)

    except KeyboardInterrupt:
        print("\n用户中断扫描")
    except Exception as e:
        print(f"扫描过程中发生错误: {e}")

    end_time = datetime.now()
    print(f"\n总耗时: {(end_time - start_time).total_seconds():.2f}秒")