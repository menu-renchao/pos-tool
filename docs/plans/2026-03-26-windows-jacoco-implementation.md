# Windows JaCoCo Integration Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Add Windows JaCoCo deployment, restore, and report generation to the existing `Windows POS` tab for one selected POS version at a time.

**Architecture:** Extend the current Windows POS GUI with a JaCoCo section, keep file-system rules in `WindowsService`, and run long operations through dedicated worker threads. The implementation should be idempotent for deployment and backup-driven for restoration so the original `setenv.bat` can be restored safely.

**Tech Stack:** Python 3, PyQt6, pytest, Windows batch scripting, existing `Backend`/`BaseWorkerThread` infrastructure

---

### Task 1: Add service-level tests for JaCoCo file operations

**Files:**
- Create: `D:\menusifu\PythonProject\rc\pos_tool_new\tests\windows_pos\test_jacoco_service.py`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\windows_pos\windows_service.py`

**Step 1: Write the failing test**

```python
def test_deploy_jacoco_creates_backup_and_report_script(tmp_path):
    service = WindowsService()
    version_dir = make_fake_version_dir(tmp_path)
    zip_path = make_fake_jacoco_zip(tmp_path, "jacoco-0.8.13")

    result = service.deploy_jacoco(str(tmp_path), "1.8.0.30.14", str(zip_path))

    assert result.success is True
    assert (version_dir / "tomcat" / "bin" / "setenv.bat.jacoco.bak").exists()
    assert "jacocoagent.jar" in (version_dir / "tomcat" / "bin" / "setenv.bat").read_text(encoding="utf-8")
    assert (version_dir / "jacoco-0.8.13" / "lib" / "buildReport.bat").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/windows_pos/test_jacoco_service.py::test_deploy_jacoco_creates_backup_and_report_script -v`
Expected: FAIL because `deploy_jacoco` and the test helpers do not exist yet.

**Step 3: Write minimal implementation**

Add helper methods in `windows_service.py` for:

```python
def get_version_path(self, base_path, selected_version):
    return os.path.join(base_path, selected_version)

def get_jacoco_backup_path(self, setenv_path):
    return f"{setenv_path}.jacoco.bak"
```

Also add a first pass of `deploy_jacoco(...)` that validates inputs, extracts the zip, backs up `setenv.bat`, injects the agent line, and writes `buildReport.bat`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/windows_pos/test_jacoco_service.py::test_deploy_jacoco_creates_backup_and_report_script -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/windows_pos/test_jacoco_service.py pos_tool_new/windows_pos/windows_service.py
git commit -m "test: cover windows jacoco deployment flow"
```

### Task 2: Make deployment idempotent and restoration backup-driven

**Files:**
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\tests\windows_pos\test_jacoco_service.py`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\windows_pos\windows_service.py`

**Step 1: Write the failing tests**

```python
def test_deploy_jacoco_twice_does_not_duplicate_agent_line(tmp_path):
    ...

def test_restore_jacoco_recovers_original_setenv_and_removes_report_script(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/windows_pos/test_jacoco_service.py -k "duplicate_agent_line or restore_jacoco" -v`
Expected: FAIL because redeploy and restore edge cases are not fully implemented.

**Step 3: Write minimal implementation**

Implement:

```python
def has_jacoco_agent(self, content):
    return "jacocoagent.jar" in content

def restore_jacoco(self, base_path, selected_version):
    ...
```

Rules:

- never duplicate the JaCoCo agent line
- create the backup only once
- restore from `setenv.bat.jacoco.bak`
- remove generated `buildReport.bat`
- keep extracted `jacoco-*` directories untouched

**Step 4: Run tests to verify they pass**

Run: `pytest tests/windows_pos/test_jacoco_service.py -k "duplicate_agent_line or restore_jacoco" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/windows_pos/test_jacoco_service.py pos_tool_new/windows_pos/windows_service.py
git commit -m "feat: support idempotent windows jacoco restore"
```

### Task 3: Add report-script generation and validation tests

**Files:**
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\tests\windows_pos\test_jacoco_service.py`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\windows_pos\windows_service.py`

**Step 1: Write the failing tests**

```python
def test_build_report_script_uses_dynamic_paths(tmp_path):
    ...

def test_generate_report_rejects_missing_runtime_dependencies(tmp_path):
    ...
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/windows_pos/test_jacoco_service.py -k "dynamic_paths or runtime_dependencies" -v`
Expected: FAIL because the script content and validation helpers are incomplete.

**Step 3: Write minimal implementation**

Implement helpers such as:

```python
def build_report_script_content(self, version_path, jacoco_root):
    ...

def validate_jacoco_report_requirements(self, version_path, jacoco_root):
    ...
```

Requirements:

- derive the JaCoCo folder name from the extracted zip contents
- create `jacocoreport` if missing
- validate `java.exe`, `jacococli.jar`, and `WEB-INF\classes`
- return structured success/error results for the UI layer

**Step 4: Run tests to verify they pass**

Run: `pytest tests/windows_pos/test_jacoco_service.py -k "dynamic_paths or runtime_dependencies" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/windows_pos/test_jacoco_service.py pos_tool_new/windows_pos/windows_service.py
git commit -m "feat: validate windows jacoco report generation"
```

### Task 4: Add worker threads for deploy, restore, and report generation

**Files:**
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\work_threads.py`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\windows_pos\windows_service.py`

**Step 1: Write the failing test or manual harness note**

There is no existing worker-thread test harness in the repo. Add a short module-level comment in the implementation plan notes and verify behavior through targeted manual UI execution after service tests pass.

**Step 2: Run the relevant service tests first**

Run: `pytest tests/windows_pos/test_jacoco_service.py -v`
Expected: PASS before adding UI-thread wiring.

**Step 3: Write minimal implementation**

Add three thread classes matching the existing Windows thread style:

```python
class DeployJacocoThread(BaseWorkerThread):
    ...

class RestoreJacocoThread(BaseWorkerThread):
    ...

class GenerateJacocoReportThread(BaseWorkerThread):
    ...
```

Each thread should emit progress text, call the corresponding `WindowsService` method, and emit a final success/failure message.

**Step 4: Run a focused import check**

Run: `python -c "from pos_tool_new.work_threads import DeployJacocoThread, RestoreJacocoThread, GenerateJacocoReportThread; print('ok')"`
Expected: `ok`

**Step 5: Commit**

```bash
git add pos_tool_new/work_threads.py pos_tool_new/windows_pos/windows_service.py
git commit -m "feat: add windows jacoco worker threads"
```

### Task 5: Integrate JaCoCo controls into the Windows POS tab

**Files:**
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\windows_pos\windows_window.py`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\pos_tool_new\work_threads.py`

**Step 1: Write the failing manual check**

Manual expectation:

- the `Windows POS` tab shows a JaCoCo zip selector
- the tab shows three new buttons
- clicking a button without required inputs shows a warning instead of crashing

**Step 2: Run the app to verify the controls are missing**

Run: `python pos_tool_new/main.py`
Expected: the `Windows POS` tab does not yet show the JaCoCo controls.

**Step 3: Write minimal implementation**

Add:

- a JaCoCo zip path input and browse button
- three JaCoCo action buttons
- handlers that:
  - validate the zip path when deploying
  - reuse `select_version(...)`
  - start the new worker threads
  - reuse the current thread-guard logic

**Step 4: Run the app to verify the controls work**

Run: `python pos_tool_new/main.py`
Expected: the `Windows POS` tab shows the new controls and each action produces logs or validation messages without blocking the UI.

**Step 5: Commit**

```bash
git add pos_tool_new/windows_pos/windows_window.py pos_tool_new/work_threads.py
git commit -m "feat: add windows jacoco controls to gui"
```

### Task 6: End-to-end verification on a sample Windows POS directory

**Files:**
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\docs\plans\2026-03-26-windows-jacoco-design.md`
- Modify: `D:\menusifu\PythonProject\rc\pos_tool_new\docs\plans\2026-03-26-windows-jacoco-implementation.md`

**Step 1: Prepare a sample local version directory**

Use a safe copy of a real or representative POS version tree with:

- `tomcat\bin\setenv.bat`
- `jre\bin\java.exe`
- `tomcat\webapps\kpos\WEB-INF\classes`
- local `jacoco-*.zip`

**Step 2: Run the deployment flow**

Run: `python pos_tool_new/main.py`
Expected: deployment creates the backup, injects JaCoCo config, and writes `buildReport.bat`.

**Step 3: Run the report-generation flow**

Run: click `Generate Coverage Report`
Expected: `jacocoreport\index.html` opens successfully.

**Step 4: Run the restore flow**

Run: click `Restore JaCoCo`
Expected: the original `setenv.bat` is restored and `buildReport.bat` is removed.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-26-windows-jacoco-design.md docs/plans/2026-03-26-windows-jacoco-implementation.md
git commit -m "docs: record windows jacoco verification notes"
```
