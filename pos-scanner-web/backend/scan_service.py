import concurrent.futures
import ipaddress
import json
import socket
import requests
from typing import List, Dict, Any


class ScanPosService:
    def __init__(self, local_ip=None):
        self.local_ip = local_ip

    @staticmethod
    def guess_os_by_ip(ip, port=22080, timeout=3):
        url = f"http://{ip}:{port}/kpos/webapp/os/getOSType"
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                data = response.json()
                return data.get("os", "Unknown")
            return "Unknown"
        except Exception:
            return "Unknown"

    def fetch_company_profile(self, ip, port=22080, timeout=5):
        url = f"http://{ip}:{port}/kpos/webapp/store/fetchCompanyProfile"
        for _ in range(2):
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response.json()
                return {"error": f"HTTP {response.status_code}"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Request error: {str(e)}"}
            except json.JSONDecodeError as e:
                return {"error": f"JSON decode error: {str(e)}"}
        return {"error": "Failed after retries"}

    def _scan_port(self, ip, port, timeout=1):
        try:
            with socket.create_connection((str(ip), port), timeout):
                return ip
        except:
            return None

    def _get_local_network(self):
        local_ip = self.local_ip if self.local_ip else socket.gethostbyname(socket.gethostname())
        return ipaddress.IPv4Network(f"{local_ip}/23", strict=False)

    def _extract_required_info(self, api_response):
        try:
            company = api_response.get("company", {})
            result = {
                "merchantId": company.get("merchantId"),
                "name": company.get("name"),
                "version": company.get("appInfo", {}).get("version"),
            }
            return {k: v for k, v in result.items() if v is not None} or {"error": "No required fields"}
        except Exception as e:
            return {"error": str(e)}

    def scan_network(self, port=22080):
        network = self._get_local_network()
        hosts = list(network.hosts())

        # 扫描开放端口
        open_ips = self._scan_open_ips(hosts, port)

        # 获取设备信息
        results = self._fetch_profiles(open_ips, port)
        return results

    def _scan_open_ips(self, hosts, port):
        open_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = {executor.submit(self._scan_port, ip, port): ip for ip in hosts}
            for future in concurrent.futures.as_completed(futures):
                if (result := future.result()):
                    open_ips.append(str(result))
        return open_ips

    def _fetch_profiles(self, open_ips, port):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(self._fetch_and_process, ip, port): ip for ip in open_ips}
            for future in concurrent.futures.as_completed(future_to_ip):
                result = future.result()
                if result:
                    results.append(result)
        return results

    def _fetch_and_process(self, ip, port):
        full_data = self.fetch_company_profile(ip, port)
        simple_data = self._extract_required_info(full_data)
        device_type = self.guess_os_by_ip(ip, port)

        return {
            "ip": ip,
            "merchantId": simple_data.get("merchantId", ""),
            "name": simple_data.get("name", ""),
            "version": simple_data.get("version", ""),
            "type": device_type,
            "status": "success" if "error" not in simple_data else "error",
            "error": simple_data.get("error", ""),
            "fullData": full_data
        }

    def get_local_ips(self):
        """获取本地所有IPv4地址"""
        ips = set()
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if "." in ip and not ip.startswith("127."):
                ips.add(ip)
        return list(ips)