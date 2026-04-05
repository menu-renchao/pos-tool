import zipfile
from pathlib import Path
import sys
import types

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

if "PyQt6" not in sys.modules:
    qtcore = types.ModuleType("PyQt6.QtCore")

    class DummySignal:
        def connect(self, *_args, **_kwargs):
            pass

        def emit(self, *_args, **_kwargs):
            pass

    class QObject:
        def __init__(self, *_args, **_kwargs):
            pass

    class QThread:
        def __init__(self, *_args, **_kwargs):
            pass

        def start(self):
            return None

        def isRunning(self):
            return False

        def quit(self):
            return None

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

from pos_tool_new.windows_pos.windows_service import WindowsService


def make_fake_version_dir(base_dir: Path, version: str = "1.8.0.30.14") -> Path:
    version_dir = base_dir / version
    setenv_path = version_dir / "tomcat" / "bin" / "setenv.bat"
    classes_dir = version_dir / "tomcat" / "webapps" / "kpos" / "WEB-INF" / "classes"
    java_path = version_dir / "jre" / "bin" / "java.exe"

    setenv_path.parent.mkdir(parents=True, exist_ok=True)
    classes_dir.mkdir(parents=True, exist_ok=True)
    java_path.parent.mkdir(parents=True, exist_ok=True)

    setenv_path.write_text(
        "@echo off\n"
        "set JAVA_OPTS=%JAVA_OPTS% -Ddemo=true\n"
        "echo start\n",
        encoding="utf-8",
    )
    java_path.write_text("fake-java", encoding="utf-8")
    (classes_dir / "Example.class").write_text("bytecode", encoding="utf-8")
    return version_dir


def make_fake_jacoco_zip(base_dir: Path, jacoco_dir_name: str = "jacoco-0.8.13") -> Path:
    zip_path = base_dir / f"{jacoco_dir_name}.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{jacoco_dir_name}/lib/jacocoagent.jar", "agent")
        archive.writestr(f"{jacoco_dir_name}/lib/jacococli.jar", "cli")
    return zip_path


def make_flat_jacoco_zip(base_dir: Path, zip_name: str = "jacoco-0.8.13.zip") -> Path:
    zip_path = base_dir / zip_name
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("lib/jacocoagent.jar", "agent")
        archive.writestr("lib/jacococli.jar", "cli")
        archive.writestr("doc/readme.txt", "doc")
    return zip_path


def test_deploy_jacoco_creates_backup_and_report_script(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    zip_path = make_fake_jacoco_zip(tmp_path, "jacoco-0.8.13")

    result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))

    assert result.success is True
    assert (version_dir / "tomcat" / "bin" / "setenv.bat.jacoco.bak").exists()
    assert "jacocoagent.jar" in (version_dir / "tomcat" / "bin" / "setenv.bat").read_text(encoding="utf-8")
    assert (version_dir / "jacoco-0.8.13" / "lib" / "buildReport.bat").exists()


def test_deploy_jacoco_twice_does_not_duplicate_agent_line(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    zip_path = make_fake_jacoco_zip(tmp_path)

    first_result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))
    second_result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))
    setenv_content = (version_dir / "tomcat" / "bin" / "setenv.bat").read_text(encoding="utf-8")
    backup_content = (version_dir / "tomcat" / "bin" / "setenv.bat.jacoco.bak").read_text(encoding="utf-8")

    assert first_result.success is True
    assert second_result.success is True
    assert setenv_content.count("jacocoagent.jar") == 1
    assert "jacocoagent.jar" not in backup_content


def test_restore_jacoco_recovers_original_setenv_and_removes_report_script(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    original_content = (version_dir / "tomcat" / "bin" / "setenv.bat").read_text(encoding="utf-8")
    zip_path = make_fake_jacoco_zip(tmp_path)

    deploy_result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))
    restore_result = service.restore_jacoco(str(tmp_path), version_dir.name)

    assert deploy_result.success is True
    assert restore_result.success is True
    assert (version_dir / "tomcat" / "bin" / "setenv.bat").read_text(encoding="utf-8") == original_content
    assert not (version_dir / "jacoco-0.8.13" / "lib" / "buildReport.bat").exists()


def test_build_report_script_uses_dynamic_paths(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path, version="9.9.9.9")

    script_content = service.build_report_script_content(version_dir, version_dir / "jacoco-custom")

    assert 'set "JRE_HOME=' in script_content
    assert "9.9.9.9\\jre" in script_content
    assert "jacoco-custom\\lib" in script_content
    assert 'if not exist "%REPORT_DIR%" mkdir "%REPORT_DIR%"' in script_content
    assert 'if "%NO_PAUSE%"=="0" pause' in script_content


def test_generate_report_rejects_missing_runtime_dependencies(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)

    result = service.validate_jacoco_report_requirements(version_dir, version_dir / "jacoco-0.8.13")

    assert result.success is False
    assert "jacococli.jar" in result.message


def test_deploy_jacoco_accepts_flat_zip_structure(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    zip_path = make_flat_jacoco_zip(tmp_path)

    result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))

    assert result.success is True
    assert (version_dir / "jacoco-0.8.13" / "lib" / "jacocoagent.jar").exists()
    assert (version_dir / "jacoco-0.8.13" / "lib" / "buildReport.bat").exists()


def test_generate_jacoco_report_runs_script_and_opens_index(tmp_path, monkeypatch):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    zip_path = make_fake_jacoco_zip(tmp_path)
    deploy_result = service.deploy_jacoco(str(tmp_path), version_dir.name, str(zip_path))
    report_index = version_dir / "jacoco-0.8.13" / "lib" / "jacocoreport" / "index.html"
    report_index.parent.mkdir(parents=True, exist_ok=True)
    report_index.write_text("<html></html>", encoding="utf-8")

    called = {"startfile": None, "cmd": None}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        called["cmd"] = (command, kwargs)
        return Completed()

    def fake_startfile(path):
        called["startfile"] = path

    monkeypatch.setattr("pos_tool_new.windows_pos.windows_service.subprocess.run", fake_run)
    monkeypatch.setattr("pos_tool_new.windows_pos.windows_service.os.startfile", fake_startfile, raising=False)

    result = service.generate_jacoco_report(str(tmp_path), version_dir.name)

    assert deploy_result.success is True
    assert result.success is True
    assert called["cmd"][0][0:2] == ["cmd", "/c"]
    assert called["cmd"][0][3:] == ["--no-open", "--no-pause"]
    assert called["startfile"] == str(report_index)
