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

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(scan_port, ip, port): ip for ip in hosts}
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                worker.scan_progress.emit((idx + 1) * 100 // len(hosts), str(futures[future]))
                if not worker._is_running:
                    return
                if (result := future.result()):
                    open_ips.append(str(result))

        worker._results = []
        for ip in open_ips:
            if not worker._is_running:
                return
            full_data = self.fetch_company_profile(ip, port)
            simple_data = extract_required_info(full_data)
            result = {
                "ip": ip,
                "merchantId": simple_data.get("merchantId", ""),
                "name": simple_data.get("name", ""),
                "version": simple_data.get("version", ""),
                "status": "success" if "error" not in simple_data else "error",
                "error": simple_data.get("error", ""),
            }
            worker._results.append(result)
            worker.scan_result.emit(result)
        worker.scan_finished.emit(worker._results)
