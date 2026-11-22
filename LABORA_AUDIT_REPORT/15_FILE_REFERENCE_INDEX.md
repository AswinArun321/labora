# LABORA — Master File Reference Index

**Inspection Baseline:** `d:\v\LABORA-Test-Windows`  
**Git Branch:** `production-integration` (Commit: `08083b0`)  

---

## 1. Active Application Source Code (`server/`)

### 1.1 Backend Configuration & Entry Points (`server/backend/labora/`)
- [server/backend/manage.py](file:///d:/v/LABORA-Test-Windows/server/backend/manage.py): Django administrative command-line utility.
- [server/backend/labora/__init__.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/__init__.py): Binds Celery app on Python module initialization.
- [server/backend/labora/celery.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/celery.py): Initializes the Celery instance (`Celery("labora")`) and autocovers tasks.
- [server/backend/labora/settings.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/settings.py): Central settings: DB engine selection, SimpleJWT, CORS, Celery broker, Judge0, Secure Browser HMAC key.
- [server/backend/labora/urls.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/urls.py): Master URL routing table, DRF router registrations, and SPA static catch-all.
- [server/backend/labora/wsgi.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/wsgi.py): WSGI entrypoint for synchronous web servers (Gunicorn).
- [server/backend/labora/asgi.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/asgi.py): ASGI entrypoint for asynchronous servers.

### 1.2 Accounts Application (`server/backend/accounts/`)
- [server/backend/accounts/models.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/models.py): Defines `Department`, `User` (roles: admin, teacher, student), `Subject`, and singleton `CollegeSettings`.
- [server/backend/accounts/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/views.py): Implements `login`, `me`, `client_status`, `college_settings`, `DepartmentViewSet`, `SubjectViewSet` (with `enroll`), and `UserViewSet` (with `import_csv`).
- [server/backend/accounts/serializers.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/serializers.py): DRF serializers: `DepartmentSerializer`, `UserSerializer`, `MeSerializer`, `SubjectSerializer`, `CollegeSettingsSerializer`.
- [server/backend/accounts/permissions.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/permissions.py): Custom RBAC permission classes: `IsAdminRole`, `IsTeacher`, `IsStudent`, `IsTeacherOrAdmin`, `ReadOnlyOrAdmin`.
- [server/backend/accounts/admin.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/admin.py): Django admin registrations for account models.
- [server/backend/accounts/tests.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/tests.py): Test file placeholder.
- [server/backend/accounts/migrations/0001_initial.py](file:///d:/v/LABORA-Test-Windows/server/backend/accounts/migrations/0001_initial.py): Initial database schema migration for `accounts`.

### 1.3 Labs Application (`server/backend/labs/`)
- [server/backend/labs/models.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/models.py): Defines `Practical`, `Submission`, `CodeVersion`, `ActivityEvent`, and `Execution` models.
- [server/backend/labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py): Implements workspace, autosave, sync run, async run, telemetry ingestion, submit, teacher review, approval, corrections, and reporting.
- [server/backend/labs/serializers.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/serializers.py): DRF serializers: `PracticalSerializer`, `StudentPracticalSerializer`, `ExecutionSerializer`, `VersionSerializer`, `EventSerializer`, `SubmissionSerializer`.
- [server/backend/labs/executor.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/executor.py): Low-level execution interface: `run_code`, `run_local` (Python/GCC/Javac subprocesses), `run_judge0` (synchronous Judge0 client).
- [server/backend/labs/tasks.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/tasks.py): Celery asynchronous worker task: `dispatch_execution_task`.
- [server/backend/labs/secure_browser.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/secure_browser.py): Cryptographic HMAC-SHA256 signature verification functions (`compute_signature`, `is_secure_browser_request`).
- [server/backend/labs/records.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/records.py): Generates official lab records in `.docx` (`build_docx`) and WeasyPrint PDF (`build_pdf`).
- [server/backend/labs/indicators.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/indicators.py): Computes academic indicators (large insertions, blocked pastes, window switches, late changes).
- [server/backend/labs/ai_review.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/ai_review.py): OpenAI-compatible LLM review generator for teachers (`summarize_submission`).
- [server/backend/labs/tests.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/tests.py): Automated test suite containing 10 test cases in `LaboraFlowTests`.
- [server/backend/labs/management/commands/seed_demo.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/management/commands/seed_demo.py): Management command to seed demo college, users, course, and C/Java/Python practicals.
- [server/backend/labs/migrations/0001_initial.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/migrations/0001_initial.py): Initial database schema migration for `labs`.
- [server/backend/labs/migrations/0002_execution_completed_at_execution_judge0_token_and_more.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/migrations/0002_execution_completed_at_execution_judge0_token_and_more.py): Schema migration adding `state`, `judge0_token`, `retry_count`, and timing fields to `Execution`.

### 1.4 Compiled Frontend (`server/frontend/dist/`)
- [server/frontend/dist/index.html](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/index.html): SPA HTML root.
- [server/frontend/dist/assets/index-DRq-BgX-.js](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/index-DRq-BgX-.js): Main React application bundle containing all page components, routing, and polling loops.
- [server/frontend/dist/assets/index-BM31NznF.css](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/index-BM31NznF.css): Minified Tailwind CSS stylesheet.
- [server/frontend/dist/assets/editor.worker-CRz__AKW.js](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/editor.worker-CRz__AKW.js): Monaco Editor core web worker.
- [server/frontend/dist/assets/cpp-C7h46wYY.js](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/cpp-C7h46wYY.js): Monaco C/C++ language worker.
- [server/frontend/dist/assets/java-BEtHBSE6.js](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/java-BEtHBSE6.js): Monaco Java language worker.
- [server/frontend/dist/assets/python-BGouXFzX.js](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/assets/python-BGouXFzX.js): Monaco Python language worker.

---

## 2. Electron Secure Browser Client (`Secure Browser/`)

- [Secure Browser/labora.config.json](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/labora.config.json): Cleartext configuration file specifying `serverUrl`, `browserKey`, and `blockedProcesses`.
- [Secure Browser/resources/app/package.json](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/package.json): Electron package metadata.
- [Secure Browser/resources/app/main.js](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/main.js): Electron main process implementing kiosk lockdown, shortcut blocking, clipboard wiping, process scanning, and HMAC request signing.
- [Secure Browser/resources/app/preload.js](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/preload.js): Context bridge exposing `window.laboraSecure` to the renderer.
- [Secure Browser/resources/app/offline.html](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/offline.html): Static offline error page rendered when server is unreachable.
- [Secure Browser/version](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/version): Reports Electron runtime version (`45.3.4`).

---

## 3. Production Deployment Kit (`production_kit/`)

- [production_kit/docker/Dockerfile.backend](file:///d:/v/LABORA-Test-Windows/production_kit/docker/Dockerfile.backend): Production Dockerfile for Django and Celery based on Python 3.11 slim with WeasyPrint libraries.
- [production_kit/docker/docker-compose.prod.yml](file:///d:/v/LABORA-Test-Windows/production_kit/docker/docker-compose.prod.yml): Docker Compose configuration for Postgres, Redis, Django, Celery, Judge0, and Nginx.
- [production_kit/docker/judge0.conf](file:///d:/v/LABORA-Test-Windows/production_kit/docker/judge0.conf): Judge0 CE resource limits configuration (CPU: 5.0s, RAM: 256MB).
- [production_kit/nginx/nginx.conf](file:///d:/v/LABORA-Test-Windows/production_kit/nginx/nginx.conf): Nginx configuration with client-based rate limiting, SSL termination, and static caching.
- [production_kit/load_testing/locustfile.py](file:///d:/v/LABORA-Test-Windows/production_kit/load_testing/locustfile.py): Realistic Locust load test scenario simulating 1,000 students and teachers.
- [production_kit/scripts/backup_postgres.sh](file:///d:/v/LABORA-Test-Windows/production_kit/scripts/backup_postgres.sh): Automated PostgreSQL backup script with gzip compression and SHA256 checksums.
- [production_kit/scripts/restore_postgres.sh](file:///d:/v/LABORA-Test-Windows/production_kit/scripts/restore_postgres.sh): PostgreSQL restoration script with checksum verification.
- [production_kit/scripts/health_check.sh](file:///d:/v/LABORA-Test-Windows/production_kit/scripts/health_check.sh): System diagnostic script auditing containers, database readiness, Redis backlog, and Judge0.
- [production_kit/runbooks/OPERATIONAL_RUNBOOKS.md](file:///d:/v/LABORA-Test-Windows/production_kit/runbooks/OPERATIONAL_RUNBOOKS.md): Standard operating procedures for service management, updates, backups, and disaster recovery.

---

## 4. Root Batch Scripts & Documentation

- [1 - START SERVER.bat](file:///d:/v/LABORA-Test-Windows/1%20-%20START%20SERVER.bat): Provisions `.venv`, runs migrations, seeds demo, and starts Django development server.
- [2 - START SECURE BROWSER.bat](file:///d:/v/LABORA-Test-Windows/2%20-%20START%20SECURE%20BROWSER.bat): Launches Secure Browser in locked fullscreen kiosk mode.
- [3 - SECURE BROWSER (windowed test mode).bat](file:///d:/v/LABORA-Test-Windows/3%20-%20SECURE%20BROWSER%20(windowed%20test%20mode).bat): Launches Secure Browser with `--dev` flag (windowed mode with DevTools).
- [RESET DEMO DATA.bat](file:///d:/v/LABORA-Test-Windows/RESET%20DEMO%20DATA.bat): Wipes SQLite database and seed flag.
- [READ ME FIRST.txt](file:///d:/v/LABORA-Test-Windows/READ%20ME%20FIRST.txt): Test instructions and demo logins.
