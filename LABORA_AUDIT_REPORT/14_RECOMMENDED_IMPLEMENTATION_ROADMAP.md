# LABORA — Phased Implementation & Engineering Roadmap

**Document Role:** Handover Roadmap for ChatGPT & Development Team  
**Audit Baseline:** `d:\v\LABORA-Test-Windows` (Branch: `production-integration`, Commit: `08083b0`)  
**Guiding Objective:** Transition from Windows Single-Machine Demo to Resilient 1,000-User Production System  

---

## Phase 1: Correctness, Integrity & Reliability Fixes

### 1. Objective
Fix immediate logic defects, data integrity flaws, and sensitive data leakage in the existing Django backend without altering core architecture.

### 2. Exact Files Involved
- `server/backend/labs/views.py` (`workspace_submit`)
- `server/backend/labs/serializers.py` (`ExecutionSerializer`)
- `server/backend/labs/views.py` (`PracticalViewSet.submissions`, `subject_report`)
- `server/backend/labs/tests.py`

### 3. Required Changes
1. **Fix Submission Verification Logic (`labs/views.py` line 312):**
   - Modify `workspace_submit` so it queries the absolute latest execution overall:
     `latest = sub.executions.order_by("-created_at").first()`
   - Assert that `latest` exists, matches the submitted code, has `status="Accepted"`, and `state=Execution.State.COMPLETED`.
   - Prevent submitting if an execution is currently in `QUEUED`, `DISPATCHING`, or `PROCESSING` state.
2. **Remove Leaked Sandbox Token (`labs/serializers.py` line 31):**
   - Strip `judge0_token` from `ExecutionSerializer.Meta.fields`.
3. **Resolve N+1 Queries in Teacher Dashboards (`labs/views.py` line 140):**
   - Refactor `compute_indicators()` in `labs/indicators.py` to evaluate prefetched `sub.versions.all()` in Python memory rather than calling `.filter()` on the database manager.

### 4. Dependencies & Prerequisites
None. Can be implemented directly on the current backend codebase.

### 5. Automated Tests & Acceptance Criteria
- **Tests to Add:**
  - `test_cannot_reuse_stale_accepted_execution_after_failed_run()`
  - `test_judge0_token_not_in_execution_serializer()`
  - `test_teacher_dashboard_query_count()` using `self.assertNumQueriesLessThan(10)`
- **Acceptance Criteria:** All unit tests pass; query count on teacher dashboard remains constant regardless of cohort size.

### 6. Risks & Mitigation
- *Risk:* Breaking submission flow if student code contains minor whitespace differences.
- *Mitigation:* Ensure `clean_code()` strip logic is applied symmetrically to both submission and execution records.

---

## Phase 2: Asynchronous Execution & Celery Worker Decoupling

### 1. Objective
Eliminate Celery worker blocking during Judge0 execution to enable high-concurrency throughput.

### 2. Exact Files Involved
- `server/backend/labs/tasks.py` (`dispatch_execution_task`)
- `server/backend/labs/views.py` (`workspace_run_async`)
- `server/backend/labora/settings.py`

### 3. Required Changes
1. **Decouple Task Dispatch from Polling Loop (`labs/tasks.py`):**
   - Option A: Configure Judge0 webhook callback URL (`callback_url`), allowing Judge0 to notify Django when finished.
   - Option B: If webhooks are unavailable, replace the synchronous `time.sleep()` loop inside `dispatch_execution_task` with a lightweight, self-rescheduling Celery task (`poll_judge0_task.apply_async(args=[ex.id], countdown=1.0)`).
2. **Handle Redis Connection Failures Gracefully (`labs/views.py` line 248):**
   - Wrap `dispatch_execution_task.delay(ex.id)` in a `try...except (OperationalError, ConnectionError):` block.
   - If Redis is down, catch the exception, mark `ex.state = Execution.State.FAILED`, and return HTTP 503 with a user-friendly error message.
3. **Execution Reaper Cron Job:**
   - Implement a Celery beat periodic task (`reap_stale_executions`) running every 2 minutes that transitions any execution stuck in `DISPATCHING` or `PROCESSING` for > 3 minutes to `TIMED_OUT`.

### 4. Dependencies
Active Redis broker.

### 5. Automated Tests & Acceptance Criteria
- **Tests to Add:**
  - `test_async_execution_with_redis_failure()`
  - `test_stale_execution_reaper()`
- **Acceptance Criteria:** A single Celery worker process can process 50 overlapping execution dispatches without worker starvation.

---

## Phase 2A (Revised Roadmap Phase): Automated Lab Record Generation Hardening [COMPLETED]

### 1. Objective
Harden document generation (DOCX and PDF), add LibreOffice headless conversion fallback, enforce XML text sanitization, implement process-isolated temporary file handling, add concurrency locking, and enable efficient streaming downloads without altering existing API routes.

### 2. Exact Files Involved
- `server/backend/labs/records.py` (`build_docx`, `build_pdf`, `_mono`, `record_context`)
- `server/backend/labs/views.py` (`_file_response`, `record_subject`, `record_single`)
- `server/backend/labs/templates/labs/record.html`
- `server/backend/labora/settings.py`
- `server/backend/labs/tests.py`

### 3. Required Changes
1. **XML Control Character Sanitization:** Strip XML-incompatible control characters (`\x00`–`\x08`, `\x0b`–`\x0c`, `\x0e`–`\x1f`) from student code, stdin, stdout, and stderr to prevent `python-docx` crashes.
2. **Dual-Engine PDF Pipeline:** Implement LibreOffice headless conversion (`soffice --headless --convert-to pdf`) as primary/fallback PDF generator with isolated user profile directories; retain WeasyPrint as alternative; handle absence of both engines gracefully with HTTP 501.
3. **Safe Temporary File Lifecycle:** Manage temporary files and conversion directories using `tempfile.TemporaryDirectory` with guaranteed deletion in `try...finally` blocks.
4. **Concurrency File Locking:** Prevent redundant simultaneous compilation of the same record using per-target locking.
5. **Streaming Downloads:** Stream output via Django's `FileResponse` to prevent buffering large files in application memory.

### 4. Dependencies
`python-docx`, `weasyprint` (optional where GTK is available), LibreOffice (`soffice`, optional system package).

### 5. Automated Tests & Acceptance Criteria
- Unit tests verifying XML sanitization on dirty stdout.
- Concurrent download generation tests for multiple students.
- Conversion failure handling tests.
- Download chunking and tempfile cleanup tests.
- Full regression test pass on existing submission and approval workflows.

---

## Phase 3: Frontend Reconstruction & Source Recovery [PENDING / PRESERVED]

### 1. Objective
Establish a clean, uncompiled React + TypeScript + Vite project to replace the single-file minified bundle in `server/frontend/dist/`.

### 2. Exact Files Involved
- New directory: `frontend/` (at project root)
- `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/`
- `server/backend/labora/settings.py` (`FRONTEND_DIST`)

### 3. Required Changes
1. Initialize Vite React + TypeScript template.
2. Install dependencies: `@monaco-editor/react`, `react-router-dom`, `lucide-react`, `tailwindcss`.
3. Implement clean component tree matching the API specifications in `07_API_DOCUMENTATION.md`:
   - `Auth`: Login page with Secure Browser error banner.
   - `Student`: Dashboard, Workspace with Monaco Editor, stdin/stdout panes, polling hook, submission modal, Records download view.
   - `Teacher`: Course list, Practical creator/editor, Submissions monitoring table with indicators, Detailed review dossier with version diff.
   - `Admin`: User management with CSV upload, Course enrollment, College branding settings.
4. Configure Vite build output to emit to `server/frontend/dist/`.

### 4. Dependencies
Node.js 18+ runtime.

### 5. Automated Tests & Acceptance Criteria
- Run `npm run build` cleanly without TypeScript or ESLint errors.
- All 10 routes render identically and pass end-to-end integration with Django backend.

---

## Phase 4: Database Optimization & Concurrency Hardening

### 1. Objective
Optimize PostgreSQL for 1,000 concurrent active users and eliminate race conditions.

### 2. Exact Files Involved
- `server/backend/labs/models.py`
- `server/backend/labs/migrations/0003_performance_indexes.py` (New migration)
- `server/backend/labs/views.py` (`workspace_submit`, `submission_approve`)

### 3. Required Changes
1. **Add Composite Indexes:**
   - Add `models.Index(fields=["submission", "created_at"])` to `ActivityEvent.Meta`.
   - Add `models.Index(fields=["submission", "status", "state", "-created_at"])` to `Execution.Meta`.
   - Add `models.Index(fields=["student", "status"])` to `Submission.Meta`.
2. **Implement Row-Level Database Locking:**
   - In `workspace_submit`, wrap operations in `with transaction.atomic():` and query submission with `Submission.objects.select_for_update().get(pk=sub.pk)`.
   - In `submission_approve`, wrap operations in `with transaction.atomic():` with `select_for_update()`.

### 4. Dependencies
PostgreSQL database.

### 5. Acceptance Criteria
- Migration applies cleanly.
- `EXPLAIN ANALYZE` confirms index scans on telemetry and execution lookups.

---

## Phase 5: Security Hardening & Client Protection

### 1. Objective
Harden production settings, prevent host RCE, and protect client integrity.

### 2. Exact Files Involved
- `server/backend/labora/settings.py`
- `Secure Browser/resources/app/main.js`
- `Secure Browser/labora.config.json`

### 3. Required Changes
1. **Enforce Production Settings Guard (`settings.py`):**
   ```python
   if not DEBUG:
       if CODE_EXECUTOR == "local":
           raise ImproperlyConfigured("Local execution prohibited when DEBUG=False.")
       if SECRET_KEY == "dev-only-insecure-key-change-me-in-production-0000":
           raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
   ```
2. **Harden Electron Client (`main.js`):**
   - Strip `--dev` command-line argument parsing from packaged production builds (`!app.isPackaged`).
   - Remove plaintext `labora.config.json` from user-writable directories; enforce Windows ACLs during MSI/InnoSetup installation.

---

## Phase 6: Production Docker & Nginx Deployment

### 1. Objective
Ensure the containerized production stack boots out-of-the-box on a fresh Ubuntu server.

### 2. Exact Files Involved
- `production_kit/docker/Dockerfile.backend`
- `production_kit/docker/docker-compose.prod.yml`
- `production_kit/nginx/nginx.conf`
- New file: `production_kit/docker/docker-entrypoint.sh`

### 3. Required Changes
1. **Container Entrypoint Script (`docker-entrypoint.sh`):**
   - Wait for PostgreSQL via `pg_isready`.
   - Run `python manage.py migrate --noinput`.
   - Run `python manage.py collectstatic --noinput`.
   - Execute Gunicorn CMD.
2. **Judge0 Sandbox Configuration (`docker-compose.prod.yml`):**
   - Add `privileged: true` and mount `/sys/fs/cgroup:/sys/fs/cgroup:ro` to `judge0-server`.
3. **Nginx SSL Bootstrap (`nginx.conf`):**
   - Provide an initial bootstrap HTTP server block to allow Let's Encrypt / Certbot verification before enabling SSL certificate directives.

---

## Phase 7: Monitoring, Backup Automation & Disaster Recovery

### 1. Objective
Implement automated monitoring and execute live disaster recovery drills on staging.

### 2. Exact Files Involved
- `production_kit/scripts/backup_postgres.sh`
- `production_kit/scripts/restore_postgres.sh`
- `production_kit/scripts/health_check.sh`
- Crontab configuration

### 3. Required Changes
1. Configure host Linux crontab to execute `backup_postgres.sh` nightly at 02:00 AM.
2. Execute live dry-run drill: Create sample data, back up, drop tables, restore, and assert 100% data fidelity.

---

## Phase 8: Progressive 1,000-User Load Testing

### 1. Objective
Rigorously prove server capacity on physical college hardware.

### 2. Exact Files Involved
- `production_kit/load_testing/locustfile.py`

### 3. Progressive Benchmark Execution
Execute Locust progressive ramp-up against the staging server:
$$50 \rightarrow 100 \rightarrow 250 \rightarrow 500 \rightarrow 750 \rightarrow 1,000 \text{ Users}$$
- **Pass SLA:** Total HTTP 5xx errors < 0.1%; P95 web latency < 800ms; P95 execution turnaround < 8.0s; zero Gunicorn worker timeouts.
