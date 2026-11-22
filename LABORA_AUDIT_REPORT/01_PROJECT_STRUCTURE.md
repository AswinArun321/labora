# LABORA — Project Structure & File Responsibility Catalog

**Inspection Scope:** Full recursive workspace inventory of `d:\v\LABORA-Test-Windows`  
**Git Branch:** `production-integration`  
**Commit Baseline:** `08083b0`  

---

## 1. Top-Level Directory Tree

```text
d:\v\LABORA-Test-Windows\
├── .git/                                      # Local Git repository
├── .gitignore                                 # Git ignore patterns
├── 1 - START SERVER.bat                       # Windows launcher for Django development server
├── 2 - START SECURE BROWSER.bat               # Windows launcher for Secure Browser in Kiosk mode
├── 3 - SECURE BROWSER (windowed test mode).bat# Windows launcher for Secure Browser in dev mode
├── READ ME FIRST.txt                          # Quick-start documentation and test guide
├── RESET DEMO DATA.bat                        # Script to clear SQLite db and demo seed file
├── delivery_evidence/                         # Historical planning, audit, and hardware docs
│   ├── Phase_0_Baseline/                      # Architecture baseline and manifest
│   ├── Phase_1_Audit/                         # Baseline source audit and debt backlog
│   ├── Phase_2_Production_Kit_Review/         # Integration gaps between baseline and production kit
│   ├── Phase_3_Dev/                           # Local development setup notes
│   ├── Phase_6_Infrastructure/                # Deployment and firewall documentation
│   ├── Phase_7_Secure_Browser/                # Client test documentation
│   ├── Phase_8_Operations/                    # Disaster recovery and operational notes
│   ├── Phase_9_Validation/                    # Performance and security test templates
│   └── Phase_10_Hardware/                     # Server hardware inventory and sizing
├── production_kit/                            # Production blueprints, Docker, Nginx, scripts
│   ├── backend_async/                         # Celery blueprint implementation files
│   ├── docker/                                # Dockerfile.backend, compose.prod, judge0.conf
│   ├── docs/                                  # Audit reports, readiness checklists, limitation notes
│   ├── load_testing/                          # Locust realistic load testing script
│   ├── nginx/                                 # Production Nginx reverse proxy configuration
│   ├── runbooks/                              # Operational runbooks (SOPs)
│   └── scripts/                               # Postgres backup, restore, and health check scripts
├── Secure Browser/                            # Packaged Electron Secure Browser application
│   ├── labora.config.json                     # Client runtime configuration (serverUrl, browserKey)
│   ├── LABORA Secure Browser.exe              # Packaged Electron executable (git-ignored)
│   ├── version                                # Electron runtime version (45.3.4)
│   └── resources/app/                         # Electron JavaScript application source
│       ├── package.json                       # Electron package metadata
│       ├── main.js                            # Electron main process (kiosk, IPC, HMAC, filters)
│       ├── preload.js                         # Context isolation bridge (laboraSecure API)
│       └── offline.html                       # Fallback error page when server is unreachable
└── server/                                    # Active application source code
    ├── backend/                               # Django 5 backend application
    │   ├── accounts/                          # User authentication, roles, subjects, departments
    │   ├── labora/                            # Django project configuration (settings, urls, celery)
    │   ├── labs/                              # Practicals, submissions, execution, records, indicators
    │   ├── db.sqlite3                         # Local development SQLite database
    │   ├── manage.py                          # Django management CLI script
    │   ├── requirements.txt                   # Production Python package dependencies
    │   ├── requirements-test.txt              # Local Windows test kit dependencies
    │   └── .env.example                       # Environment variable template
    └── frontend/                              # Frontend web application
        └── dist/                              # Compiled Vite / React production bundle
            ├── favicon.svg                    # Application favicon
            ├── icons.svg                      # UI sprite icons
            ├── index.html                     # SPA HTML entry point
            └── assets/                        # Compiled CSS, JS bundles, and Monaco workers
```

---

## 2. Detailed Responsibility of Every Project File

### Root Directory
- `1 - START SERVER.bat`: Windows batch script. Detects Python 3.10+, provisions `.venv`, installs `requirements-test.txt`, runs `manage.py migrate`, seeds initial demo data (`manage.py seed_demo --secure-langs c`), sets `CODE_EXECUTOR=local`, opens `http://127.0.0.1:8000` in the default browser, and launches `manage.py runserver 127.0.0.1:8000 --noreload`.
- `2 - START SECURE BROWSER.bat`: Launches `Secure Browser\LABORA Secure Browser.exe` in locked fullscreen kiosk mode.
- `3 - SECURE BROWSER (windowed test mode).bat`: Launches `Secure Browser\LABORA Secure Browser.exe` with `--dev` flag, enabling window resizing, developer tools, and disabling keyboard lockouts.
- `RESET DEMO DATA.bat`: Deletes `server\backend\db.sqlite3` and `server\backend\.seeded`, returning the development database to a fresh state.
- `READ ME FIRST.txt`: User guide explaining test logins (`admin/admin123`, `teacher/teacher123`, `student1/student123`), how to test restricted practicals, clipboard isolation, and local execution requirements.
- `.gitignore`: Ignores `.venv/`, `__pycache__/`, `*.pyc`, `db.sqlite3`, `.seeded`, and large executable `Secure Browser/LABORA Secure Browser.exe`.

### Server Backend (`server/backend/`)
- `manage.py`: Django standard command-line utility for administrative tasks.
- `requirements.txt`: Defines production dependencies including `psycopg[binary]`, `weasyprint`, `gunicorn`, `celery`, `redis`, `djangorestframework`, `djangorestframework-simplejwt`, `django-cors-headers`, `python-docx`.
- `requirements-test.txt`: Minimal dependencies for Windows local testing without native C/GTK dependencies (`psycopg` and `weasyprint` omitted).
- `.env.example`: Documents all environment variable keys, descriptions, and defaults for production and local environments.
- `db.sqlite3`: Active SQLite database file used when `POSTGRES_DB` environment variable is not defined.

#### Project Configuration (`server/backend/labora/`)
- `__init__.py`: Imports Celery app (`from .celery import app as celery_app`) so `@shared_task` binds on startup.
- `settings.py`: Core configuration. Reads environment variables from host or `.env`. Defines database switching (SQLite vs PostgreSQL), JWT authentication lifetimes (60m access, 12h refresh), CORS headers, rate limits, Celery broker URLs, Judge0 connection details, Secure Browser HMAC secret, and frontend static asset paths.
- `urls.py`: Master routing configuration. Connects DRF routers (`departments`, `subjects`, `users`, `practicals`), specific API routes (`auth/`, `workspace/`, `executions/`, `submissions/`, `records/`, `reports/`), Django admin (`django-admin/`), and optional fallback routing for `server/frontend/dist/index.html`.
- `celery.py`: Initializes the Celery application (`app = Celery("labora")`) using Django settings namespace `CELERY`.
- `wsgi.py`: WSGI entry point for synchronous web servers like Gunicorn.
- `asgi.py`: ASGI entry point for asynchronous servers.

#### Accounts Application (`server/backend/accounts/`)
- `models.py`: Defines authoritative identity and institutional models:
  - `Department`: Academic department (name, code).
  - `User`: Custom user model extending `AbstractUser` with role choices (`admin`, `teacher`, `student`), department FK, roll number, semester, and batch.
  - `Subject`: Course definition (code, name, semester, academic year, department FK) with M2M relations to `teachers` and `students`.
  - `CollegeSettings`: Singleton model (pk=1) storing college name, address, logo, report titles, and the boolean `students_secure_browser_only`.
- `views.py`: API views for account management:
  - `login`: Validates credentials, issues SimpleJWT access/refresh tokens, enforces Secure Browser restriction for students if enabled.
  - `me`: Returns profile details for the authenticated user.
  - `client_status`: Read-only check verifying if the caller's request carries a valid Secure Browser HMAC signature.
  - `college_settings`: GET/PUT/PATCH endpoint for institutional branding (admin only for modifications).
  - `DepartmentViewSet`: CRUD viewset for academic departments.
  - `SubjectViewSet`: CRUD viewset for subjects with custom `enroll` action.
  - `UserViewSet`: CRUD viewset for users with custom `import_csv` bulk onboarding action.
- `serializers.py`: DRF serializers for `Department`, `User`, `MeSerializer`, `Subject`, and `CollegeSettings`.
- `permissions.py`: Custom RBAC permission classes: `IsAdminRole`, `IsTeacher`, `IsStudent`, `IsTeacherOrAdmin`, `ReadOnlyOrAdmin`.
- `admin.py`: Registers account models with Django admin interface.
- `tests.py`: Test placeholder for accounts app.

#### Labs Application (`server/backend/labs/`)
- `models.py`: Defines laboratory examination and submission domain models:
  - `Practical`: Lab problem statement (experiment_no, title, aim, question, language [C, Java, Python], starter code, sample input, restricted flag, require_secure_browser flag, is_published, due_date).
  - `Submission`: Student work container (practical FK, student FK, code, status [`in_progress`, `submitted`, `correction`, `approved`], result text, teacher_note, record_execution FK, timestamps).
  - `CodeVersion`: Historical snapshot of code taken on autosave, run, or submit.
  - `ActivityEvent`: Audit telemetry event (kind [`session_start`, `insert`, `delete`, `internal_paste`, `paste_blocked`, `drop_blocked`, `focus_lost`, `focus_back`, `fullscreen_exit`, `secure_alert`, `run`, `submit`], character count, detail JSON, client timestamp, secure browser flag).
  - `Execution`: Individual code run record (submission FK, code, stdin, stdout, stderr, compile_output, state [`QUEUED`, `DISPATCHING`, `SUBMITTED_TO_RUNNER`, `PROCESSING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`], status string, time, memory, judge0_token, runner_url, timestamps).
- `views.py`: Core laboratory API endpoints:
  - `PracticalViewSet`: CRUD for practicals (teachers) and list (students), with `submissions` dashboard action.
  - `workspace`: Loads practical instructions, starter code, submission state, and logs `session_start` event.
  - `workspace_save`: Saves code draft and creates `CodeVersion` (autosave).
  - `workspace_run`: Synchronous execution endpoint (executes and blocks HTTP request).
  - `workspace_run_async`: Asynchronous execution endpoint (creates `Execution(state=QUEUED)` and enqueues Celery task).
  - `execution_detail`: Enforces student/teacher isolation and returns status/outputs of an execution.
  - `workspace_events`: Batched ingestion endpoint for client telemetry events.
  - `workspace_submit`: Validates that submitted code matches an accepted execution and locks submission.
  - `submission_detail`: Returns full teacher review dossier (code, versions, events, executions, indicators).
  - `submission_approve`: Teacher approval endpoint.
  - `submission_request_correction`: Teacher correction request endpoint.
  - `submission_ai_summary`: Optional AI code structure analysis.
  - `record_overview`, `record_subject`, `record_single`: Endpoints returning generated DOCX/PDF lab records.
  - `subject_report`: Progress statistics across practicals for teachers/admins.
- `executor.py`: Low-level code runner interface:
  - `run_code`: Selects between `run_local` and `run_judge0`.
  - `run_local`: Unsandboxed local execution using `subprocess.run` (Python, GCC, Javac).
  - `run_judge0`: Synchronous Judge0 REST call with `wait=true`.
- `tasks.py`: Asynchronous Celery execution worker task (`dispatch_execution_task`):
  - Dispatches job to Judge0 with `wait=false`.
  - Polls Judge0 until completion or timeout.
  - Updates `Execution` model and creates `ActivityEvent(kind='run')`.
- `records.py`: Generates official institutional laboratory records in Microsoft Word (`.docx`) and WeasyPrint PDF formats using stored execution results.
- `secure_browser.py`: Cryptographic HMAC-SHA256 signature verification functions (`compute_signature`, `is_secure_browser_request`).
- `indicators.py`: Rule-based anomaly detection algorithms flagging large insertions, blocked pastes, window switches, secure alerts, normal browser usage, and late changes.
- `ai_review.py`: Integration with OpenAI-compatible chat completion APIs (OpenAI or Gemini) for teacher-side code analysis.
- `tests.py`: Comprehensive test suite containing 10 test cases covering authentication, secure browser gates, multi-language execution, async flow, submission validation, and permissions.
- `management/commands/seed_demo.py`: Seeds initial college settings, department, admin, teacher, 4 students, and 3 practicals (C, Java, Python).

### Server Frontend (`server/frontend/dist/`)
- `index.html`: Single-page application entry point.
- `favicon.svg`, `icons.svg`: SVG icon sprite and favicon.
- `assets/index-DRq-BgX-.js`: Minified React 18 application bundle (1.1 MB). Contains React Router DOM, Tailwind UI components, workspace editor, polling loop, teacher review interface, and admin dashboards.
- `assets/index-BM31NznF.css`: Minified Tailwind CSS stylesheet.
- `assets/editor.worker-CRz__AKW.js`: Monaco Editor core web worker.
- `assets/cpp-C7h46wYY.js`: Monaco C/C++ language worker.
- `assets/java-BEtHBSE6.js`: Monaco Java language worker.
- `assets/python-BGouXFzX.js`: Monaco Python language worker.

### Electron Secure Browser (`Secure Browser/`)
- `labora.config.json`: Runtime configuration holding `serverUrl`, cleartext `browserKey`, `clearClipboardOnBlur`, `processCheckSeconds`, and `blockedProcesses` list.
- `resources/app/package.json`: Electron manifest defining app name, version (`1.0.0`), and main entry point `main.js`.
- `resources/app/main.js`: Main Electron process. Implements fullscreen kiosk, window event interception (blocking Alt+F4, F5, F11, F12, Ctrl+W), clipboard flushing on blur/focus/exit, HTTP request interceptor attaching `X-Labora-Ts` and `X-Labora-Signature` headers, process scanner (`tasklist`), and IPC handlers (`labora:quit`, `labora:retry`).
- `resources/app/preload.js`: Sandboxed context bridge exposing `window.laboraSecure` to the web page.
- `resources/app/offline.html`: Static fallback UI rendered when connection to the LABORA server fails.

### Production Kit (`production_kit/`)
- `backend_async/`: Reference/blueprint code for Celery asynchronous architecture (`async_views.py`, `celery.py`, `models_extension.py`, `tasks.py`).
- `docker/Dockerfile.backend`: Multi-stage Python 3.11 slim Dockerfile with WeasyPrint system dependencies (Pango, Cairo, GdkPixbuf) and non-root `labora` user.
- `docker/docker-compose.prod.yml`: Docker Compose stack defining 6 services: `db` (Postgres 16), `redis` (Redis 7), `backend` (Django/Gunicorn), `celery_worker` (Celery), `judge0-server`, `judge0-db`, `judge0-redis`, and `nginx`.
- `docker/judge0.conf`: Resource limit configuration for Judge0 CE (CPU limit: 5.0s, RAM limit: 256MB).
- `nginx/nginx.conf`: Nginx configuration with client-based rate limiting (`limit_req_zone`), SSL termination, and static asset caching.
- `load_testing/locustfile.py`: Realistic Locust load testing scenario simulating up to 1,000 students and teachers.
- `runbooks/OPERATIONAL_RUNBOOKS.md`: Comprehensive sysadmin operational runbooks covering lifecycle, deployment, backups, disaster recovery, and troubleshooting.
- `scripts/backup_postgres.sh`: Automated backup script creating gzip-compressed, SHA256-checksummed database dumps.
- `scripts/restore_postgres.sh`: Safe database restoration script with checksum verification.
- `scripts/health_check.sh`: Shell diagnostic script checking containers, database readiness, Redis queue backlog, and Judge0 connectivity.
- `docs/`: 13 specialized engineering reports, integration gap analyses, and readiness checklists.

### Delivery Evidence (`delivery_evidence/`)
- Contains historical project documents from earlier development phases (`Phase_0` through `Phase_10`), including hardware inventory, baseline manifests, and test baseline templates.

---

## 3. Git Repository Status & Commit History

```text
Branch: production-integration
Tracking: origin/production-integration
Working Tree: Clean (No uncommitted changes)

Recent Commits:
08083b0 Ignore large executable files
b98955b docs(audit): add final verification report, readiness checklist, load test results, security audit, and blocked tests inventory
181e143 fix(prod-kit): resolve Dockerfile copy, alpine nginx headers, client-based rate limiting, and execution routing alias
c5ab27a feat(frontend): integrate asynchronous execution flow and polling in React workspace
3a1ad3e feat(async-execution): implement celery and judge0 asynchronous execution, state machine, and tests
403276f baseline: initial commit of LABORA project
```

### Git Branches & Tags
- `master`: Initial baseline commit (`403276f`).
- `production-integration`: Active working branch containing asynchronous Celery integration, frontend polling patch, and production kit fixes.
- No Git tags or stashes exist.
