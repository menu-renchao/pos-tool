import socket
import ipaddress
import concurrent.futures
from PyQt6.QtCore import QObject
from pos_tool_new.backend import Backend
from pos_tool_new.work_threads import ScanPrinterWorkerThread

class ScanPrinterService(Backend, QObject):
    def __init__(self, local_ip=None):
        super().__init__()
        self.worker = None
        self.local_ip = local_ip

    def start_scan(self, ports=(9100, 10009)):
        if self.worker and self.worker.isRunning():
            return
        self.worker = ScanPrinterWorkerThread(self, ports)
        return self.worker

    def scan_network(self, worker, ports=(9100, 10009)):
        network = self._get_local_network()
        hosts = list(network.hosts())
        open_ips = self._scan_open_ips(worker, hosts, ports)
        worker._results = open_ips
        worker.scan_finished.emit(open_ips)

    def _scan_ports(self, ip, ports, timeout=1):
        return [port for port in ports if self._is_port_open(ip, port, timeout)]

    def _is_port_open(self, ip, port, timeout):
        try:
            with socket.create_connection((str(ip), port), timeout):
                return True
        except:
            return False

    def _get_local_network(self):
        local_ip = self.local_ip or socket.gethostbyname(socket.gethostname())
        return ipaddress.IPv4Network(f"{local_ip}/23", strict=False)

    def _scan_open_ips(self, worker, hosts, ports):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            futures = {executor.submit(self._scan_ports, ip, ports): ip for ip in hosts}
            for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                worker.scan_progress.emit((idx + 1) * 100 // len(hosts), str(futures[future]))
                if not worker._is_running:
                    return results
                open_ports = future.result()
                if open_ports:
                    results.append({
                        "ip": str(futures[future]),
                        "open_ports": open_ports,
                        "type": self._get_device_type(open_ports, str(futures[future]))
                    })
        return results

    def _get_device_type(self, open_ports, ip=None):
        if 9100 in open_ports:
            return self._check_zebra_printer(ip) or "打印机"
        if 10009 in open_ports:
            return "刷卡机"
        return "未知设备"

    def _check_zebra_printer(self, ip):
        try:
            import requests
            resp = requests.get(f'http://{ip}', timeout=2)
            if resp.ok and ('Zebra' in resp.text or 'ZD411' in resp.text):
                return "标签打印机"
        except:
            pass
        return None

    def test_print(self, ip, port=9100):
        try:
            device_type = self._get_device_type([port], ip)
            if device_type == "标签打印机":
                # 标签打印机发送ZPL，去除样式，字体小一点，IP换行显示
                data = f'^XA^FO50,50^A0N,20,20^FDTest Print:^FS^FO50,80^A0N,20,20^FD{ip}^FS^XZ'.encode('utf-8')
            else:
                data = b'\x1b@' + f'test:{ip}\n\n\n\n\n\n\n\n\n\n'.encode('gb18030') + b'\x1dV\x00'
            with socket.create_connection((ip, port), timeout=3) as s:
                s.sendall(data)
        except Exception as e:
            print(f"打印机测试打印失败: {ip}:{port} {e}")

    def print_label(self, ip, text, port=9100):
        try:
            zpl = '^XA'
            zpl += '^CW1,E:SIMSUN.TTF'  # 选择SimSun字体
            zpl += '^SEE:GB18030.DAT'  # 选择GB18030编码表
            zpl += '^CI26'  # 选择GB18030字符集
            y = 50
            for line in text.splitlines():
                zpl += f'^FO50,{y}^A1N,30,30^FD{line}^FS'
                y += 40
            zpl += '^XZ'
            data = zpl.encode('gb18030')  # 用GB18030编码
            with socket.create_connection((ip, port), timeout=3) as s:
                s.sendall(data)
        except Exception as e:
            print(f"标签打印失败: {ip}:{port} {e}")
