# Phase 1: LABORA Source-Code Audit Report

**Audited Baseline:** `LABORA-Test-Windows`  
**Inspection Date:** 22 November 2026  
**Standards Reference:** `LABORA_updated_completion_plan.md` Phase 1  

---

## 1. Executive Technical Summary

The LABORA codebase was audited line-by-line across all 18 inspection areas defined in the plan. The findings confirm that the core application domain logic is well-architected, normalized, and functional. 

Crucially, the audit confirms the central hypothesis raised in previous planning documents:
> **The code execution subsystem in the test kit is 100% synchronous.** In `server/backend/labs/views.py` (lines 208-212), `workspace_run` blocks the HTTP worker thread while executing untrusted student code, and in `server/backend/labs/executor.py` (line 60), calls Judge0 with `wait=true`. This is completely untenable for 1,000 concurrent users and represents the primary engineering gap that must be addressed before production.

---

## 2. Detailed Findings Across 18 Audit Areas

### Area 1: Repository Structure and Entry Points
* Root contains Windows development batch launchers and packaged Electron client.
* Server application cleanly segregated into `server/backend/` (Django) and `server/frontend/dist/` (compiled React assets).
* Ready for production containerization.

### Area 2: Django/Python Dependencies & Settings
* Django 5.0+, Django REST Framework 3.15+, SimpleJWT 5.3+, django-cors-headers 4.3+.
* Document generation relies on `python-docx` and `weasyprint`.
* Settings use robust environment variable fallbacks via `os.environ.get()`.

### Area 3: Frontend Build & Monaco Integration
* The frontend is delivered as a pre-compiled Vite bundle in `server/frontend/dist/`.
* Monaco language workers (`cpp-*.js`, `java-*.js`, `python-*.js`, `editor.worker-*.js`) are correctly isolated and packaged.
* Served seamlessly by Django's catch-all `re_path` rule in single-server mode.

### Area 4: Electron Secure Browser Architecture
* Built on Electron 34.0.0.
* Sandboxed renderer process (`nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`).
* Preload bridge (`preload.js`) exposes read-only methods via `contextBridge.exposeInMainWorld('laboraSecure')`.

### Area 5: Authentication & Access Control
* Custom `User` model inheriting `AbstractUser`.
* Roles: `ADMIN`, `TEACHER`, `STUDENT`.
* Fine-grained permissions implemented in `accounts/permissions.py` (`IsAdminRole`, `IsTeacher`, `IsStudent`, `ReadOnlyOrAdmin`).
* Login rate limiting (`LoginThrottle`: 20/min).

### Area 6 & 7: Academic Hierarchies & Practical Workflow
* `Department` -> `Subject` -> `Practical` -> `Submission`.
* Students can only view practicals for subjects in which they are explicitly enrolled.
* Teachers can only grade submissions for subjects they teach.

### Area 8: Editor State, Autosave & Version History
* Student code is autosaved via `POST /api/workspace/<id>/save/`.
* Incremental versions are tracked in `labs_codeversion` with reason flags (`autosave`, `run`, `submit`).
* Student workspace automatically rehydrates the latest version on launch or reconnect.

### Area 9, 10 & 11: Execution Engine & Judge0 Integration
* **Synchronous Bottleneck Confirmed:** In `labs/views.py`:
  ```python
  res = run_code(p.language, code, stdin) # BLOCKS HTTP REQUEST THREAD
  ```
* In `labs/executor.py`:
  ```python
  url = settings.JUDGE0_URL.rstrip("/") + "/submissions?base64_encoded=true&wait=true"
  resp = requests.post(url, json=payload, headers=headers, timeout=60) # SYNCHRONOUS
  ```
* **Execution Persistence Defect Confirmed:** `Execution` database records are created only *after* code execution returns. If the process is killed or timed out by the web server, no execution trace exists.

### Area 12: Activity Event Logging & Indicators
* Granular client telemetry captured in `ActivityEvent` (insert, delete, paste_blocked, focus_lost, etc.).
* Heuristic engine (`labs/indicators.py`) computes 6 neutral indicators: `large_insertion`, `blocked_paste`, `left_window`, `secure_alert`, `normal_browser`, `late_changes`.

### Area 13: Submission Locking & Teacher Workflow
* Students must execute accepted code matching their final submission before submitting.
* Submissions in `submitted` or `approved` state are locked against edits (`ensure_editable` raises 403).
* Teachers can approve or request corrections (which unlocks editing).

### Area 14: PDF & DOCX Lab Record Generation
* Tamper-proof: Output in records is extracted directly from `record_execution.stdout`.
* DOCX generation works on all platforms.
* PDF generation via `weasyprint` requires GTK libraries (native on Linux, requires runtime on Windows).

### Area 15: Database Schema & Migrations
* Schema is normalized with proper foreign keys and unique constraints.
* Django migration files (`0001_initial.py`) exist and apply cleanly.

### Area 16: Scripts & Secret Handling
* Windows batch files provide convenience for local evaluation.
* Default keys in `.env.example` must be rotated before production deployment.

### Area 17 & 18: Test Suite & Reproducibility
* Test suite in `labs/tests.py` covers 8 core integration scenarios.
* **Test Defect Discovered:** In `labs/tests.py` line 30:
  `call_command("seed_demo", stdout=open("/dev/null", "w"))`
  Fails on native Windows because `/dev/null` is POSIX-specific. On Windows, tests must use `os.devnull` or `io.StringIO()`.
