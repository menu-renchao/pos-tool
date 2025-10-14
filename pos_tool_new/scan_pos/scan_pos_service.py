import re
import subprocess

from PyQt6.QtCore import QObject
from pos_tool_new.backend import Backend
from pos_tool_new.work_threads import ScanPosWorkerThread
import requests
import json
import socket
import ipaddress
import concurrent.futures


class ScanPosService(Backend, QObject):
    def get_ttl(ip):
        try:
            output = subprocess.check_output(f'ping -n 1 {ip}', shell=True, encoding='gbk')
            match = re.search(r'TTL=(\d+)', output, re.IGNORECASE)
            if not match:
                match = re.search(r'TTL=(\d+)', output, re.IGNORECASE)
            if match:
                return int(match.group(1))
        except Exception as e:
            print(f'Error: {e}')
        return None

    def guess_os_by_ttl(ttl):
        if ttl == 128:
            return "Windows"
        elif ttl == 64:
            return "Ubuntu"
        elif ttl == 255:
            return "Router/Cisco Device"
        else:
            return "Unknown OS"

    def __init__(self):
        super().__init__()
        self.worker = None

    def start_scan(self, port=22080):
        if self.worker and self.worker.isRunning():
            return
        self.worker = ScanPosWorkerThread(self, port)
        return self.worker

    @staticmethod
    def fetch_company_profile(ip, port=22080, timeout=5):
        url = f"http://{ip}:{port}/kpos/webapp/store/fetchCompanyProfile"
        for _ in range(2):
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response.json()
                return {"error": f"HTTP {response.status_code}"}
            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                return {"error": str(e)}
        return {"error": "Failed after retries"}

    def scan_network(self, worker, port=22080):
        def scan_port(ip, port, timeout=1):
            try:
                with socket.create_connection((str(ip), port), timeout):
                    return ip
            except:
                return None

        def get_local_network():
            local_ip = socket.gethostbyname(socket.gethostname())
            return ipaddress.IPv4Network(f"{local_ip}/23", strict=False)

        def extract_required_info(api_response):
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

        network = get_local_network()
        hosts = list(network.hosts())
        open_ips = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = {executor.submit(scan_port, ip, port): ip for ip in hosts}
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                worker.scan_progress.emit((idx + 1) * 100 // len(hosts), str(futures[future]))
                if not worker._is_running:
                    return
                if (result := future.result()):
                    open_ips.append(str(result))

        worker._results = []
        def fetch_and_emit(ip):
            if not worker._is_running:
                return None
            full_data = self.fetch_company_profile(ip, port)
            simple_data = extract_required_info(full_data)
            ttl = ScanPosService.get_ttl(ip)
            device_type = ScanPosService.guess_os_by_ttl(ttl) if ttl else "——"
            result = {
                "ip": ip,
                "merchantId": simple_data.get("merchantId", ""),
                "name": simple_data.get("name", ""),
                "version": simple_data.get("version", ""),
                "type": device_type,
                "status": "success" if "error" not in simple_data else "error",
                "error": simple_data.get("error", ""),
            }
            worker.scan_result.emit(result)
            return result
        # 并发fetch_company_profile
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(fetch_and_emit, ip): ip for ip in open_ips}
            for future in concurrent.futures.as_completed(future_to_ip):
                res = future.result()
                if res:
                    worker._results.append(res)
        worker.scan_finished.emit(worker._results)
