# Windows JaCoCo One-Click Integration Design

**Date:** 2026-03-26

**Goal:** Add a Windows-only JaCoCo workflow to the existing `Windows POS` tab so users can deploy JaCoCo to a single POS version, restore the original startup configuration, and generate a coverage report from the GUI.

## Scope

- Integrate into the existing `Windows POS` tab.
- Target one selected version directory at a time.
- Assume the user already has a local `jacoco-*.zip` package.
- Provide three actions:
  - `Deploy JaCoCo`
  - `Restore JaCoCo`
  - `Generate Coverage Report`

## User Flow

1. User opens the existing `Windows POS` tab.
2. User keeps the base path pointed at `C:\Wisdomount\Menusifu\application` or another equivalent root.
3. For deployment, user selects a local `jacoco-*.zip` file and then selects one version directory.
4. The tool extracts the package into the selected version directory, updates `tomcat\bin\setenv.bat`, and writes `jacoco-*\lib\buildReport.bat`.
5. User restarts POS and executes test cases.
6. User clicks `Generate Coverage Report`; the tool runs the generated bat file and opens the generated `index.html`.
7. If needed, user clicks `Restore JaCoCo` to restore the original `setenv.bat` and remove the generated report script.

## Architecture

### UI Layer

`pos_tool_new/windows_pos/windows_window.py`

- Add a dedicated JaCoCo group in the existing `Windows POS` tab.
- Add a local zip selector for `jacoco-*.zip`.
- Add three buttons for deploy, restore, and report generation.
- Reuse existing base-path and version-selection behavior.
- Start background worker threads for all JaCoCo actions so the GUI stays responsive.

### Service Layer

`pos_tool_new/windows_pos/windows_service.py`

- Add JaCoCo-specific path resolution helpers.
- Add deployment logic:
  - validate the selected version directory
  - extract the JaCoCo zip under the version directory
  - detect the extracted root directory name dynamically
  - backup `setenv.bat` to `setenv.bat.jacoco.bak` on first deployment
  - inject a JaCoCo agent line after a `set JAVA_OPTS` line when possible
  - fall back to appending a marked JaCoCo block if no suitable insertion point exists
  - generate `buildReport.bat` under `jacoco-*\lib`
- Add restore logic:
  - restore `setenv.bat` from `setenv.bat.jacoco.bak`
  - delete the generated `buildReport.bat`
  - keep the extracted `jacoco-*` directory intact
- Add report-generation logic:
  - validate required files before execution
  - run `buildReport.bat`
  - confirm `jacocoreport\index.html` exists
  - open the report in the default browser

### Worker Layer

`pos_tool_new/work_threads.py`

- Add three Windows worker threads:
  - deploy thread
  - restore thread
  - report-generation thread
- Reuse the existing `BaseWorkerThread` style and signal contract.

## File and Script Rules

### `setenv.bat`

- First deployment creates `setenv.bat.jacoco.bak` if it does not already exist.
- Deployment is idempotent:
  - if JaCoCo agent configuration already exists, do not inject a second copy
  - still regenerate `buildReport.bat` if it is missing
- Restore prefers whole-file backup restoration instead of line deletion.

### Agent Configuration

The injected line follows this shape, with paths resolved from the selected version and extracted JaCoCo directory:

```bat
set JAVA_OPTS=%JAVA_OPTS%  -javaagent:C:/.../jacocoagent.jar=includes=com.wisdomount.*,output=tcpserver,port=9527,address=127.0.0.1,append=true -Xverify:none
```

The implementation must normalize the path to the selected version and actual extracted JaCoCo folder instead of hardcoding `1.8.0.30.14` or `0.8.13`.

### `buildReport.bat`

The generated script is based on the approved flow, with dynamic paths and a small hardening improvement: ensure the report directory exists before dumping `jacoco.exec`.

Expected runtime dependencies:

- `jre\bin\java.exe`
- `jacoco-*\lib\jacococli.jar`
- `tomcat\webapps\kpos\WEB-INF\classes`

## Error Handling

- Missing base path, version directory, zip file, `setenv.bat`, `java.exe`, or `jacococli.jar` should fail fast with a clear log message.
- Existing JaCoCo deployment should log a skip rather than duplicate configuration.
- Restore without backup should fail safely and explain why.
- Report generation should surface both process failures and missing output files.

## Testing Strategy

Implementation should add service-level tests around file operations using temporary directories.

Recommended coverage:

- deploy into a fake version directory with a valid `setenv.bat`
- redeploy without duplicating the JaCoCo agent line
- restore from backup
- generate `buildReport.bat` with dynamic paths
- fail report generation when required files are missing

## Non-Goals

- Downloading JaCoCo from the internet
- Bulk deployment to multiple version directories
- Automatic POS restart as part of deployment
- Removing the entire extracted `jacoco-*` directory during restore
