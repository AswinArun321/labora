# Phase 0: Source Inventory & File Catalog

**Project:** LABORA — Secure Programming Practical Platform  
**Baseline Date:** 22 November 2026  
**Status:** Baseline Recorded and Verified  
**Total Tracked Files:** 142 files (excluding ephemeral virtual environment and build caches)

---

## 1. Root Distribution Files
* `1 - START SERVER.bat` (1,674 bytes) — Automates Python venv check, migration, demo seeding (`manage.py seed_demo --secure-langs c`), local code execution mode, and runs Django development server on port 8000.
* `2 - START SECURE BROWSER.bat` (158 bytes) — Spawns `LABORA Secure Browser.exe` in fullscreen kiosk mode.
* `3 - SECURE BROWSER (windowed test mode).bat` (150 bytes) — Spawns `LABORA Secure Browser.exe --dev` (windowed, resizable, DevTools enabled).
* `READ ME FIRST.txt` (2,052 bytes) — Test kit quickstart documentation, prerequisites (Python 3.10+), and demo credentials.
* `RESET DEMO DATA.bat` (139 bytes) — Resets local demo state by deleting `db.sqlite3` and `.seeded`.
* `plann.md` (38,819 bytes) — Initial infrastructure & production implementation plan.
* `LABORA_updated_completion_plan.md` (24,890 bytes) — Version 2.0 completion roadmap and delivery plan.

---

## 2. Secure Browser Client (`Secure Browser/`)
* **Executable & Runtime:** `LABORA Secure Browser.exe` (249,906,688 bytes), `version` (6 bytes: Electron 34.0.0), Chromium runtime DLLs (`dxcompiler.dll`, `d3dcompiler_47.dll`, `ffmpeg.dll`, `vk_swiftshader.dll`, `vulkan-1.dll`, etc.), locale packs (`locales/*.pak`), and V8 context snapshots (`v8_context_snapshot.bin`, `snapshot_blob.bin`).
* **Configuration:** `labora.config.json` (689 bytes) — Defines default `serverUrl` (`http://127.0.0.1:8000`), shared `browserKey` (`change-this-shared-browser-key`), `clearClipboardOnBlur` (true), `processCheckSeconds` (30), and an extensive blocklist of 32 prohibited processes (chatgpt, claude, copilot, cursor, vscode, discord, zoom, teams, etc.).
* **Application Assets (`resources/app/`):**
  - `package.json` (115 bytes) — Electron metadata (`name: labora-secure-browser`, `version: 1.0.0`, `main: main.js`).
  - `main.js` (10,883 bytes) — Core Electron main process: kiosk isolation, single instance lock, window content protection (`setContentProtection(true)`), keyboard shortcut interception (Alt+F4, F5, F11, Ctrl+W, etc.), periodic process scanner (`tasklist`), display scanner (`screen.getAllDisplays()`), clipboard sanitization, and cryptographic HMAC-SHA256 request signing (`X-Labora-Ts`, `X-Labora-Signature`, `X-Labora-Client`).
  - `preload.js` (506 bytes) — Context isolation bridge exposing `window.laboraSecure` (`isSecureBrowser`, `onAlert`, `quit`, `retry`).
  - `offline.html` (1,525 bytes) — Offline fallback screen shown when server connection drops.

---

## 3. Django Web Server & REST API (`server/backend/`)
* **Core Project Configuration (`labora/`):**
  - `settings.py` (6,834 bytes) — Multi-environment settings (JWT lifetime, CORS origins, SQLite vs PostgreSQL, local vs Judge0 execution, Secure Browser HMAC tolerance, AI summary configuration).
  - `urls.py` (2,483 bytes) — Centralized routing for accounts, labs, JWT auth, and React SPA fallback (`re_path`).
  - `wsgi.py` / `asgi.py` (389 bytes each) — Application entry points.
* **Accounts Subsystem (`accounts/`):**
  - `models.py` (3,279 bytes) — `Department`, `Subject`, `User` (Admin/Teacher/Student), `CollegeSettings`.
  - `views.py` (6,181 bytes) — Authentication (`login`, `me`, `client_status`), bulk CSV import, enrollment.
  - `permissions.py` (1,049 bytes) — Role-based access control (`IsAdminRole`, `IsTeacher`, `IsStudent`).
  - `serializers.py` (3,057 bytes) — Serializers for accounts models.
  - `migrations/0001_initial.py` (10,075 bytes) — Initial schema migration.
* **Labs Subsystem (`labs/`):**
  - `models.py` (5,831 bytes) — `Practical`, `Submission`, `CodeVersion`, `ActivityEvent`, `Execution`.
  - `views.py` (19,967 bytes) — Student workspace (`workspace`, `workspace_save`, `workspace_run`, `workspace_events`, `workspace_submit`), teacher review (`submission_detail`, `submission_approve`, `submission_request_correction`, `submission_ai_summary`), and lab record downloads (`record_subject`, `record_single`).
  - `secure_browser.py` (1,380 bytes) — Server-side HMAC-SHA256 signature verification and timestamp skew validation.
  - `executor.py` (4,704 bytes) — Dual execution engine (`run_local` via Python/gcc/javac subprocesses and `run_judge0` via synchronous REST API).
  - `indicators.py` (2,981 bytes) — 6 neutral heuristic review indicators for teachers.
  - `records.py` (5,396 bytes) — DOCX generation (`python-docx`) and PDF generation (`weasyprint`).
  - `ai_review.py` (1,914 bytes) — Optional teacher-side AI summary (OpenAI/Gemini compatible).
  - `templates/labs/record.html` (3,252 bytes) — Template for PDF lab record generation.
  - `management/commands/seed_demo.py` (4,128 bytes) — Demo database seeder.
  - `tests.py` (7,952 bytes) — Integration test suite.

---

## 4. Frontend Single Page Application (`server/frontend/dist/`)
* `index.html` (456 bytes) — Root HTML mounting the React app.
* `assets/index-DRq-BgX-.js` (3,038,033 bytes) — Compiled React 18 application bundle.
* `assets/index-BM31NznF.css` (131,615 bytes) — Compiled styling.
* `assets/editor.worker-CRz__AKW.js` (303,774 bytes) — Monaco editor web worker.
* `assets/cpp-C7h46wYY.js`, `java-BEtHBSE6.js`, `python-BGouXFzX.js` — Language syntax modules.
