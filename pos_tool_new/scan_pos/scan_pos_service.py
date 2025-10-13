# 集成Backend，实现扫描逻辑
from pos_tool_new.backend import Backend
from pos_tool_new.work_threads import ScanPosWorkerThread
from PyQt6.QtCore import QObject

class ScanPosService(Backend, QObject):
    def __init__(self):
        Backend.__init__(self)
        QObject.__init__(self)
        self.worker = None

    def start_scan(self, port=22080):
        if self.worker is not None and self.worker.isRunning():
            return  # 已有扫描在进行
        self.worker = ScanPosWorkerThread(self, port)
        return self.worker

    def scan_network(self, worker, port=22080):
        import socket, ipaddress, concurrent.futures, requests, json
        def scan_port(ip, port, timeout=1):
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
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return ipaddress.IPv4Network(f"{local_ip}/23", strict=False)
        def fetch_company_profile(ip, port=22080, timeout=3):
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
            if "error" in api_response:
                return {"error": api_response["error"]}
            try:
                result = {
                    "merchantId": api_response.get("company", {}).get("merchantId"),
                    "name": api_response.get("company", {}).get("name"),
                    "version": api_response.get("company", {}).get("appInfo", {}).get("version")
                }
                if not any(result.values()):
                    return {"error": "响应中未找到所需字段"}
                return result
            except Exception as e:
                return {"error": f"数据提取错误: {str(e)}"}
        network = get_local_network()
        hosts = list(network.hosts())
        open_ips = []
        total = len(hosts)
        # 扫描端口
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = {executor.submit(scan_port, ip, port): ip for ip in hosts}
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                ip = futures[future]
                percent = int((idx + 1) / total * 100)
                worker.scan_progress.emit(percent, str(ip))
                if not worker._is_running:
                    return
                try:
                    result = future.result()
                    if result:
                        open_ips.append(str(result))
                except Exception as e:
                    pass
        # 获取公司信息
        worker._results = []
        for idx, ip in enumerate(open_ips):
            if not worker._is_running:
                return
            api_response = fetch_company_profile(ip, port)
            if "error" in api_response:
                result = {"ip": ip, "status": "error", "error": api_response["error"]}
            else:
                extracted_info = extract_required_info(api_response)
                if "error" in extracted_info:
                    result = {"ip": ip, "status": "error", "error": extracted_info["error"]}
                else:
                    result = {"ip": ip, "status": "success", **extracted_info}
            worker._results.append(result)
            worker.scan_result.emit(result)
        worker.scan_finished.emit(worker._results)
