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
    def __init__(self):
        super().__init__()
        self.worker = None

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
            except requests.exceptions.RequestException as e:
                return {"error": f"Request error: {str(e)}"}
            except json.JSONDecodeError as e:
                return {"error": f"JSON decode error: {str(e)}"}
        return {"error": "Failed after retries"}

    def scan_network(self, worker, port=22080):
        network = self._get_local_network()
        hosts = list(network.hosts())
        open_ips = self._scan_open_ips(worker, hosts, port)
        worker._results = []
        self._fetch_profiles_and_emit(worker, open_ips, port)
        worker.scan_finished.emit(worker._results)

    def _scan_port(self, ip, port, timeout=1):
        try:
            with socket.create_connection((str(ip), port), timeout):
                return ip
        except:
            return None

    def _get_local_network(self):
        local_ip = socket.gethostbyname(socket.gethostname())
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

    def _scan_open_ips(self, worker, hosts, port):
        open_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = {executor.submit(self._scan_port, ip, port): ip for ip in hosts}
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                worker.scan_progress.emit((idx + 1) * 100 // len(hosts), str(futures[future]))
                if not worker._is_running:
                    return open_ips
                if (result := future.result()):
                    open_ips.append(str(result))
        return open_ips

    def _fetch_and_emit(self, worker, ip, port):
        if not worker._is_running:
            return None
        full_data = self.fetch_company_profile(ip, port)
        simple_data = self._extract_required_info(full_data)
        device_type = self.guess_os_by_ip(ip, port)
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

    def _fetch_profiles_and_emit(self, worker, open_ips, port):
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ip = {executor.submit(self._fetch_and_emit, worker, ip, port): ip for ip in open_ips}
            for future in concurrent.futures.as_completed(future_to_ip):
                res = future.result()
                if res:
                    worker._results.append(res)
