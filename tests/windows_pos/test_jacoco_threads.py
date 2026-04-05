from dataclasses import dataclass
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if "PyQt6" not in sys.modules:
    qtcore = types.ModuleType("PyQt6.QtCore")

    class DummySignal:
        def __init__(self):
            self.connected = []

        def emit(self, *_args, **_kwargs):
            pass

        def connect(self, callback):
            self.connected.append(callback)

    class QObject:
        def __init__(self, *_args, **_kwargs):
            pass

    class QThread:
        def __init__(self, *_args, **_kwargs):
            self._running = False

        def start(self):
            self._running = True

        def isRunning(self):
            return self._running

        def quit(self):
            self._running = False

        def wait(self):
            return None

    def pyqtSignal(*_args, **_kwargs):
        return DummySignal()

    qtcore.QObject = QObject
    qtcore.QThread = QThread
    qtcore.pyqtSignal = pyqtSignal

    pyqt6 = types.ModuleType("PyQt6")
    pyqt6.QtCore = qtcore

    sys.modules["PyQt6"] = pyqt6
    sys.modules["PyQt6.QtCore"] = qtcore

if "paramiko" not in sys.modules:
    paramiko = types.ModuleType("paramiko")

    class SSHClient:
        pass

    class AutoAddPolicy:
        pass

    paramiko.SSHClient = SSHClient
    paramiko.AutoAddPolicy = AutoAddPolicy
    sys.modules["paramiko"] = paramiko

from pos_tool_new.work_threads import DeployJacocoThread, GenerateJacocoReportThread, RestoreJacocoThread


@dataclass
class DummyResult:
    success: bool
    message: str


class DummyService:
    def __init__(self):
        self.calls = []

    def deploy_jacoco(self, base_path, selected_version, zip_path):
        self.calls.append(("deploy", base_path, selected_version, zip_path))
        return DummyResult(True, "deploy ok")

    def restore_jacoco(self, base_path, selected_version):
        self.calls.append(("restore", base_path, selected_version))
        return DummyResult(True, "restore ok")

    def generate_jacoco_report(self, base_path, selected_version):
        self.calls.append(("report", base_path, selected_version))
        return DummyResult(True, "report ok")

    def log(self, *_args, **_kwargs):
        pass


def test_deploy_jacoco_thread_calls_service():
    service = DummyService()

    thread = DeployJacocoThread(service, "base", "version", "jacoco.zip")
    thread._run_impl()

    assert service.calls == [("deploy", "base", "version", "jacoco.zip")]


def test_restore_jacoco_thread_calls_service():
    service = DummyService()

    thread = RestoreJacocoThread(service, "base", "version")
    thread._run_impl()

    assert service.calls == [("restore", "base", "version")]


def test_generate_jacoco_report_thread_calls_service():
    service = DummyService()

    thread = GenerateJacocoReportThread(service, "base", "version")
    thread._run_impl()

    assert service.calls == [("report", "base", "version")]
