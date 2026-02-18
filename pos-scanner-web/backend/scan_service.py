import concurrent.futures
import ipaddress
import json
import logging
import socket
import requests
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def fetch_company_profile(self, ip, port=22080, timeout=5, max_retries=2):
        url = f"http://{ip}:{port}/kpos/webapp/store/fetchCompanyProfile"
        last_error = None
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response.json()
                last_error = f"HTTP {response.status_code}"
                logger.warning(f"获取设备信息失败 {ip}: {last_error} (尝试 {attempt + 1}/{max_retries})")
            except requests.exceptions.RequestException as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(f"请求异常 {ip}: {last_error} (尝试 {attempt + 1}/{max_retries})")
            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {str(e)}"
                logger.warning(f"JSON解析失败 {ip}: {last_error} (尝试 {attempt + 1}/{max_retries})")
        logger.error(f"获取设备信息最终失败 {ip}: {last_error}")
        return {"error": f"Failed after {max_retries} retries: {last_error}"}

    def _scan_port(self, ip, port, timeout=2):
        """扫描指定IP的端口是否开放

        Args:
            ip: 目标IP地址
            port: 目标端口
            timeout: 连接超时时间（秒），默认2秒
        """
        try:
            with socket.create_connection((str(ip), port), timeout):
                return ip
        except socket.timeout:
            logger.debug(f"端口扫描超时: {ip}:{port}")
            return None
        except ConnectionRefusedError:
            logger.debug(f"连接被拒绝: {ip}:{port}")
            return None
        except Exception as e:
            logger.debug(f"端口扫描异常 {ip}:{port}: {type(e).__name__}")
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
        logger.info(f"开始扫描网络 {network}，共 {len(hosts)} 个IP")

        # 扫描开放端口
        open_ips = self._scan_open_ips(hosts, port)
        logger.info(f"端口扫描完成，发现 {len(open_ips)} 个开放端口")

        # 获取设备信息
        results = self._fetch_profiles(open_ips, port)
        success_count = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"扫描完成，成功获取 {success_count}/{len(results)} 台设备信息")
        return results

    def _scan_open_ips(self, hosts, port):
        open_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = {executor.submit(self._scan_port, ip, port): ip for ip in hosts}
            for future in concurrent.futures.as_completed(futures):
                if (result := future.result()):
                    open_ips.append(str(result))
                    logger.debug(f"发现开放端口: {result}:{port}")
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