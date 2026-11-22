# LABORA — Project Completion Plan

**Prepared from:** `LABORA-Test-Windows(2).zip`  
**Review date:** 22 November 2026  
**Project:** LABORA — Secure Programming Practical Examination and Digital Lab Record Management System  
**Target:** One college, with a long-term objective of up to 1,000 concurrent active users  
**Deployment preference:** Self-hosted on college-owned hardware, using free/open-source software where practical

---

## 1. Purpose of this plan

This document is the implementation roadmap for taking the uploaded LABORA project from its current development/pilot state to a secure, maintainable, production deployment.

The plan is based on inspection of the uploaded source tree. It distinguishes:

- **Implemented in source:** code or configuration is present.
- **Previously tested (reported):** an included report claims a test passed; the original test environment/output may not be available in this ZIP.
- **Needs verification:** the source exists, but must be tested in the target environment.
- **Not implemented / incomplete:** a required change is still missing.
- **Blocked by infrastructure:** cannot be proven without the college Linux server, PostgreSQL, Redis, Judge0, or representative hardware.

A report saying `VERIFIED` is not, by itself, proof that the current source snapshot has passed that test. The actual source and fresh test output take precedence.

## 2. Current project snapshot

### 2.1 Components found

| Component | Current location | Snapshot assessment |
|---|---|---|
| Django backend | `server/backend/` | Main application source is present |
| Accounts and academic data | `server/backend/accounts/` | User, role, department/subject and enrollment code is present |
| Practical/workspace workflow | `server/backend/labs/` | Models, views, serializers, execution, records and tests are present |
| Database | `server/backend/db.sqlite3` | Development/demo SQLite database is included |
| Frontend | `server/frontend/dist/` | Compiled Vite/React assets only; editable React source is absent |
| Secure Browser | `Secure Browser/` | Packaged Electron runtime and `resources/app` source are present |
| Production kit | `production_kit/` | Docker, Nginx, Judge0, scripts, Locust scenario and operational documents are present |
| Audit and delivery evidence | `LABORA_AUDIT_REPORT/`, `delivery_evidence/` | Useful historical analysis and reports are included |
| Git metadata | `.git/` | Repository metadata is included in the ZIP |

### 2.2 Core features already represented in the source

- Student, teacher and administrator roles.
- Academic hierarchy and subject enrollment.
- Practical/workspace APIs.
- Code autosave, code versions and activity events.
- Python, C and Java execution paths.
- Synchronous and asynchronous execution endpoints.
- Submission, teacher review, correction and approval workflow.
- DOCX/PDF lab-record generation.
- Electron Secure Browser with navigation restrictions, kiosk behavior and request signing.
- Docker Compose production stack, Nginx configuration, backup/restore scripts and a Locust test scenario.

These are source-level observations, not a claim that every feature has been re-tested from a clean installation.

### 2.3 Important discrepancies and blockers found

| Priority | Finding in uploaded source | Why it matters | Required action |
|---|---|---|---|
| Critical | `server/backend/labs/tasks.py` still polls Judge0 in a `while` loop using `time.sleep()` | A Celery worker remains occupied while waiting for Judge0; throughput degrades under concurrent runs | Replace inline polling with a separate self-rescheduling poll task |
| Critical | `Secure Browser/resources/app/main.js` accepts `--dev` and `LABORA_DEV` | A packaged client may be launched in a less restrictive mode | Make development mode unavailable in packaged builds and test the built executable |
| Critical | `Secure Browser/labora.config.json` contains a readable shared HMAC key | A key distributed to student machines can be extracted and copied; HMAC is not proof of a trustworthy device | Redesign the trust model; do not treat this key as strong device attestation |
| Critical | `server/backend/labora/settings.py` permits `CODE_EXECUTOR=local` without a production guard | Local execution runs student code on the backend host | Fail closed if production settings use the local runner |
| Critical | `production_kit/docker/docker-compose.prod.yml` contains fallback production passwords/secrets | A deployment can accidentally start with known credentials | Require secrets from an external `.env`/secret source and reject placeholders |
| Critical | Compose starts Nginx with certificate paths that may not exist on first boot | Initial deployment can fail before certificates are provisioned | Add a documented HTTP bootstrap / certificate provisioning sequence |
| High | React source tree is absent; only `server/frontend/dist/` exists | Feature changes require editing generated/minified assets and are difficult to maintain | Recover the original source or reconstruct a clean React + TypeScript project |
| High | `production_kit/backend_async/` is separate from the active Django app | It may represent an alternative implementation, not the code currently used by Django | Compare it with active code; do not copy it over blindly |
| High | No active polling reaper/reconciliation mechanism was found in the active task implementation | Worker interruption can leave executions stuck in intermediate states | Add safe stale-task reconciliation after defining recovery semantics |
| High | `models.py` has few explicit performance indexes beyond basic state/time/token indexes | Dashboard, execution and telemetry queries may become expensive at scale | Profile real queries and add evidence-based indexes/migrations |
| High | The Nginx configuration references `login_limit` and `client_id` variables; the full configuration must be validated against the actual image/config | Undefined or incorrectly mapped variables can prevent startup or rate-limit incorrectly | Run `nginx -t` inside the production image and test rate limits |
| High | Secure Browser client key is shared across distributed clients | Any student with access to the installed files can potentially forge signed requests | Treat browser signatures as a deterrent only unless a stronger enrollment/attestation design is implemented |
| Medium | The ZIP contains a development SQLite database and `.git` metadata | Unnecessary data/repository exposure if this ZIP is distributed | Exclude local DB, secrets and repository metadata from release packages |
| Medium | Reports disagree on commit IDs, test counts and implementation status | The documentation may not describe this exact source snapshot | Re-run tests and regenerate evidence from this snapshot |

### 2.4 Current test evidence

- `server/backend/labs/tests.py` contains **13 test methods** in the uploaded source.
- Included reports refer to a 10-test run, while the earlier development conversation reported 13 tests passing after Phase 1. These are different pieces of evidence and should not be combined into one current test claim.
- The uploaded ZIP does not itself prove a fresh test run against this exact snapshot.
- The report documents explicitly identify Linux cgroups validation, live worker interruption, backup/restore drills and 1,000-user load testing as blocked or not runtime-tested.
- The performance report includes targets and workload estimates. It is not a measured 1,000-user benchmark.

**Immediate rule:** run the current source test suite before making further changes and save the output as fresh evidence.

---

## 3. Completion strategy and phase order

Do not start with a full rewrite. Preserve the existing working application and make controlled, testable changes. Each phase should be committed separately.

### Phase 0 — Establish a clean, reproducible baseline

**Goal:** Make sure every subsequent change is based on a known source snapshot.

**Tasks**
1. Create a separate backup of the uploaded project and database.
2. Record the current branch, commit hash, working-tree status and file inventory.
3. Keep the current ZIP unchanged as the recovery point.
4. Create a clean development environment using the documented Python version.
5. Install dependencies from `server/backend/requirements.txt`.
6. Run:
   ```powershell
   cd server\backend
   python manage.py check
   python manage.py showmigrations
   python manage.py test labs
   ```
7. Record test count, duration, failures and environment details.
8. Confirm whether the local database contains data that must be retained; never run reset/demo-data scripts against real college data.

**Acceptance criteria**
- Django system check passes.
- Migrations are understood and applied to a disposable test database.
- All current tests pass, or every failure is recorded before implementation begins.
- A rollback copy exists.

**Deliverables:** baseline report, test output, backup and baseline Git commit/tag.

---

### Phase 1 — Complete non-blocking Judge0 execution (highest priority) [COMPLETED]

**Status:** Completed and verified in Git checkpoint `efa7130`.
- Decoupled `dispatch_execution_task` and `poll_execution_task`.
- Removed all `time.sleep()` calls from the execution path.
- Handled Redis broker failures in `workspace_run_async` with HTTP 503 and safe FAILED transition.
- Handled ambiguous POST timeouts with `SUBMITTED_TO_RUNNER` to prevent duplicate code execution.
- Added Celery Beat stale task reconciliation (`reconcile_stale_executions`).
- All 22 tests passing.

---

### Phase 2A (Revised Active Phase) — Automated Lab Record Generation Hardening [COMPLETED]

**Status:** Completed and verified (31/31 tests passing).
- Implemented robust XML 1.0 control character sanitization preserving valid tabs, newlines, carriage returns, and all Unicode/Indian language text.
- Implemented dual-engine PDF generation pipeline (LibreOffice headless primary/fallback with isolated user profiles + WeasyPrint HTML engine).
- Implemented process-safe kernel file locking (`record_generation_lock`) supporting Windows (`msvcrt`) and Linux (`fcntl`).
- Implemented chunked streaming downloads with guaranteed post-stream cleanup (`StreamingRecordResponse`).
- Preserved existing endpoints, headers, and Windows development environment without external dependencies.

**Goal:** Ensure 100% reliable, production-ready DOCX and PDF generation, LibreOffice headless fallback, safe concurrency locking, and chunked download streaming.

**Active files**
- `server/backend/labs/records.py`
- `server/backend/labs/views.py`
- `server/backend/labs/templates/labs/record.html`
- `server/backend/labora/settings.py`
- `server/backend/labs/tests.py`

**Tasks**
1. **DOCX Generation Hardening:**
   - Sanitize all text (code, stdin, stdout, stderr, aim, result) to strip XML-illegal control characters that crash `python-docx`.
   - Set defensive table styles, explicit column widths, and robust paragraph spacing.
   - Verify logo path existence before adding pictures.
2. **PDF Generation Dual-Engine Support:**
   - Detect LibreOffice (`soffice` / `libreoffice`) availability dynamically across Windows and Linux.
   - Implement LibreOffice headless conversion (`--headless --convert-to pdf`) from DOCX to PDF.
   - Isolate LibreOffice user profile per process (`-env:UserInstallation`) to prevent multi-process crashes.
   - Retain WeasyPrint as an alternative PDF engine where system GTK/Pango libraries are available.
   - Fall back gracefully to HTTP 501 with user-friendly instructions when neither engine is available.
3. **Safe Temporary File Lifecycle & Concurrency Locking:**
   - Manage temporary conversion directories via `tempfile.TemporaryDirectory` with guaranteed cleanup in `try...finally`.
   - Implement per-record concurrency locks to prevent redundant duplicate builds when multiple concurrent requests arrive for the same student record.
4. **Streaming Downloads:**
   - Replace memory-buffered `HttpResponse` with chunked `FileResponse` for streaming large documents.
5. **Testing & Verification:**
   - Add unit tests for XML sanitization, concurrent generation, conversion failure recovery, download streaming, and temporary file cleanup.
   - Preserve existing teacher approval and student submission workflows.

---

### Phase 2B (Original Phase 2) — Recover or rebuild the frontend source [PENDING / PRESERVED]

**Goal:** Stop maintaining the frontend by editing minified build output. (Preserved as pending per project roadmap).

**Current state:** only `server/frontend/dist/` is present in the uploaded ZIP. No editable React source, `package.json` or Vite configuration was found in the project frontend directory.

**Tasks**
1. Search the developer's other local folders, Git remotes, old branches and backups for the original React source before rebuilding.
2. If source cannot be recovered, create a new frontend workspace, preferably:
   - React
   - TypeScript
   - Vite
   - Monaco Editor
   - React Router
3. Configure its build output to `server/frontend/dist/` so Django/Nginx continue serving the expected directory.
4. Recreate screens against the existing API contract rather than changing backend routes unnecessarily:
   - Login and role-based routing.
   - Student dashboard and practical list.
   - Student workspace with Monaco, stdin/stdout, run status, autosave and submission.
   - Student lab records and downloads.
   - Teacher subject/practical management.
   - Teacher live submissions list and review dossier.
   - Admin account, department, subject, enrollment and college settings screens.
5. Centralize API calls, JWT handling, error handling and polling.
6. Add loading, empty, validation, permission and network-error states.
7. Add frontend tests for critical flows.
8. Compare rebuilt behavior with the current compiled UI before replacing the production bundle.

**Acceptance criteria**
- Reproducible `npm install` and production build.
- No manual editing of generated/minified assets.
- Student, teacher and admin flows work against the current Django API.
- Monaco workers and language assets load correctly.
- The built app is served from the expected `server/frontend/dist/` path.

---

### Phase 3 — Secure the backend and execution boundary

**Goal:** Ensure production cannot accidentally expose the host to student code or rely on client-side secrets as strong authentication.

**Active files**
- `server/backend/labora/settings.py`
- `server/backend/labs/executor.py`
- `server/backend/labs/secure_browser.py`
- `server/backend/labs/views.py`
- `server/backend/.env.example`
- `Secure Browser/resources/app/main.js`
- `Secure Browser/resources/app/preload.js`
- `Secure Browser/labora.config.json`
- Electron packaging/build configuration, if available

**Backend tasks**
1. Add production startup guards:
   - `DEBUG` must be false.
   - A strong `DJANGO_SECRET_KEY` must be supplied.
   - `CODE_EXECUTOR=local` must be rejected when `DEBUG=False`.
   - Production must use the configured isolated Judge0 service.
2. Review `ALLOWED_HOSTS`, CORS, CSRF, HTTPS, secure cookies, proxy headers and JWT lifetimes.
3. Enforce strong password policy and account provisioning/reset procedures.
4. Review authorization on every student, teacher and admin endpoint, including object-level ownership and enrollment.
5. Review request size limits, rate limits, throttling, login protection and audit logging.
6. Ensure internal runner tokens/errors are never exposed through API serializers or frontend responses.
7. Review data retention for code versions and activity events.

**Secure Browser tasks**
1. Ensure `--dev` and `LABORA_DEV` only work when the app is not packaged; a production binary must not be able to enter the development mode.
2. Test kiosk escape shortcuts, navigation, pop-ups, downloads, clipboard behavior, process monitoring and multi-display alerts on actual Windows lab machines.
3. Protect configuration file permissions during installation.
4. Do not claim that a shared HMAC key embedded in a student-distributed executable proves device trust. Assume it can be extracted.
5. Decide what the Secure Browser is intended to provide: controlled UI and deterrence, or a stronger institutional device-trust mechanism. If stronger trust is required, design a separate enrollment/credential strategy with revocation and key rotation.
6. Document limitations: the browser cannot prevent use of a second physical device or guarantee that the operating system itself is uncompromised.

**Judge0 tasks**
1. Deploy Judge0 only on Linux with the required isolation features.
2. Verify CPU, memory, process, filesystem and wall-time limits.
3. Keep Judge0 endpoints private to the application network.
4. Do not enable broad container privileges merely to make startup succeed. Validate the official Judge0 requirements and apply the minimum host/container permissions required.
5. Run hostile-code tests only in an isolated staging environment.

**Acceptance criteria**
- Production settings fail closed on insecure configuration.
- Local execution is impossible in production.
- No claim of secure device attestation based solely on a distributed shared key.
- Linux sandbox tests pass on the target kernel.

---

### Phase 4 — Database correctness and performance

**Goal:** Prepare the data layer for sustained use and concurrent writes.

**Active files**
- `server/backend/labs/models.py`
- `server/backend/accounts/models.py`
- `server/backend/labs/views.py`
- New migration files under the relevant app migration directories

**Tasks**
1. Profile real SQL generated by:
   - student dashboard/practical list,
   - workspace load,
   - autosave,
   - activity event ingestion,
   - teacher submission list,
   - submission detail/review,
   - execution polling.
2. Identify N+1 queries and use `select_related()` / `prefetch_related()` where justified.
3. Add indexes only for observed high-frequency filters/orderings. Candidate areas include:
   - activity events by submission and time,
   - executions by submission and creation time/state,
   - submissions by student/status,
   - enrollment lookup paths.
4. Add database constraints where they protect invariants, including unique version numbering and one submission per student/practical.
5. Use `transaction.atomic()` and `select_for_update()` for submission, approval and execution-claim transitions where race conditions are possible.
6. Test on PostgreSQL. SQLite does not provide equivalent row-lock behavior.
7. Review PostgreSQL connection limits and application worker counts together. Add a connection pool only if measurements justify it.
8. Plan retention/archive policies for old telemetry and code versions.

**Acceptance criteria**
- Migrations apply cleanly to a copy of the current database and a fresh database.
- Concurrency tests cover duplicate submissions, approval races and execution dispatch.
- Query plans and timings are captured before and after indexes.
- No data is lost during migration.

---

### Phase 5 — Make production deployment reproducible

**Goal:** Start the full stack reliably on a fresh supported Linux server.

**Active files**
- `production_kit/docker/docker-compose.prod.yml`
- `production_kit/docker/Dockerfile.backend`
- `production_kit/nginx/nginx.conf`
- `production_kit/docker/judge0.conf`
- `production_kit/scripts/`
- `server/backend/.env.example`

**Tasks**
1. Create a production `.env` template with no usable default passwords or secret keys.
2. Add startup validation that rejects placeholder credentials and missing required environment variables.
3. Confirm Docker build context and Dockerfile paths from the documented deployment directory.
4. Add an entrypoint/startup sequence that waits for PostgreSQL, runs migrations and collects static assets before starting Gunicorn.
5. Add health checks and dependency readiness for PostgreSQL, Redis, Django, Celery, Judge0 and Nginx.
6. Define the first-run TLS process:
   - initial HTTP-only Nginx configuration,
   - domain/DNS validation,
   - certificate provisioning,
   - switch to HTTPS configuration,
   - certificate renewal test.
7. Validate Nginx config in the actual Nginx container. Confirm every referenced variable/zone is defined and that rate limiting uses the intended client identity.
8. Keep PostgreSQL, Redis and Judge0 internal; expose only the intended web ports.
9. Decide whether the college will use one server for a small pilot or two servers for larger-scale operation.
10. Document Windows developer mode separately from Linux production deployment.

**Acceptance criteria**
- `docker compose config` succeeds.
- Every container builds and becomes healthy on a fresh Linux host.
- First boot works before certificates exist, and HTTPS works after provisioning.
- No default production secrets remain.
- Rebooting the host brings the stack back without manual repair.

---

### Phase 6 — Operations, backup and recovery

**Goal:** Make the system supportable during a real examination.

**Tasks**
1. Configure automated PostgreSQL backups with a documented retention schedule.
2. Back up uploaded media and any required configuration separately.
3. Encrypt backups at rest and restrict access.
4. Perform a restore into a clean staging database; compare record counts and checksums.
5. Test recovery after:
   - Django restart,
   - Celery worker restart,
   - Redis restart,
   - Judge0 restart,
   - host reboot,
   - disk-space exhaustion simulation.
6. Add monitoring for CPU, RAM, disk, PostgreSQL connections, Redis memory, Celery queue depth, Judge0 health, HTTP errors and execution latency.
7. Add log rotation and centralized logs.
8. Prepare operational runbooks for exam start, exam end, account issues, stuck executions, backup restore and incident response.
9. Define data retention and semester-end archival/deletion procedures.

**Acceptance criteria**
- Backup schedule runs automatically.
- A restore drill succeeds and is documented.
- An operator can identify and recover from a stuck execution without editing the database manually.
- Monitoring alerts on service failure and resource exhaustion.

---

### Phase 7 — Controlled pilot

**Goal:** Validate the whole product with real users before campus-wide rollout.

**Tasks**
1. Deploy to the college staging/production-like Linux host.
2. Use PostgreSQL, Redis, Celery and isolated Judge0; do not use the local runner.
3. Pilot with one or two lab sections (approximately 30–60 students).
4. Run complete sessions covering:
   - login and enrollment,
   - Secure Browser launch,
   - practical access,
   - autosave and activity telemetry,
   - Python/C/Java execution,
   - compilation/runtime errors,
   - final submission,
   - teacher correction and approval,
   - DOCX/PDF record downloads.
5. Record incidents, queue depth, execution times, browser failures and teacher feedback.
6. Verify backup during the pilot and restore a copy into staging.
7. Fix pilot issues and repeat the affected tests.

**Acceptance criteria**
- At least two complete pilot sessions finish without data loss.
- No unresolved critical security or submission-integrity defects.
- Teachers can complete review and record generation.
- Operational staff can run the system using the runbooks.

---

### Phase 8 — Progressive performance and 1,000-user validation

**Goal:** Measure actual capacity on the intended college hardware. The 1,000-user target remains unverified until this phase passes.

**Existing asset:** `production_kit/load_testing/locustfile.py`

**Tasks**
1. Review the Locust scenario to ensure it reflects the actual current API, authentication flow and realistic student behavior.
2. Use a separate load-generator machine so the server is not competing with Locust for CPU/RAM.
3. Run progressive tests: 50 → 100 → 250 → 500 → 750 → 1,000 users.
4. At each stage measure:
   - request rate and latency percentiles,
   - HTTP 4xx/5xx rates,
   - autosave/event write latency,
   - execution queue depth and wait time,
   - Judge0 throughput and resource usage,
   - Celery worker utilization,
   - PostgreSQL connections, locks and slow queries,
   - CPU, memory, disk and network.
5. Include a realistic execution mix; do not have every virtual user submit a compile job simultaneously unless running a separate stress test.
6. Run soak tests long enough to expose memory leaks and queue buildup.
7. Tune Gunicorn workers, Celery concurrency, PostgreSQL limits, Redis and Judge0 capacity based on measurements, not guesses.
8. Repeat the benchmark after any major tuning.

**Suggested initial acceptance gates** (confirm with the college and revise based on actual exam needs):
- HTTP 5xx error rate below 0.1%.
- No lost or duplicated submissions.
- No executions permanently stuck in a non-terminal state.
- P95 autosave and telemetry latency below the agreed target.
- Execution queue wait and turnaround within the agreed exam-time SLA.
- No worker timeouts, database connection exhaustion or host memory exhaustion.

**Important:** A report containing estimated latency figures or a Locust script is not a completed load test. Save the actual Locust CSV/HTML output and server metrics for each stage.

---

## 4. Recommended immediate next steps

Do these in order:

1. **Baseline the exact ZIP:** run `manage.py check` and `manage.py test labs` and capture the full output.
2. **Complete Phase 1:** replace the active blocking Judge0 polling task with non-blocking dispatch/poll tasks and tests.
3. **Run the test suite again:** do not proceed if existing workflows regress.
4. **Test Redis/Celery/Judge0 live:** first on a development/staging environment, then on Linux.
5. **Harden production settings and Secure Browser:** remove unsafe production fallbacks and restrict development mode.
6. **Recover/rebuild frontend source:** avoid further direct edits to the minified bundle.
7. **Validate Docker/Nginx on Linux:** fix first-boot and secret-management issues.
8. **Run pilot, then load testing:** do not claim 1,000-user readiness before real measurements.

---

## 5. Definition of done

LABORA can be considered ready for a controlled college pilot when:

- The backend checks and test suite pass from a clean setup.
- Student, teacher and administrator workflows are verified end to end.
- Asynchronous execution does not block workers while polling.
- Production cannot use the unsafe local code runner.
- The Secure Browser's documented protections and limitations are understood.
- PostgreSQL, Redis, Celery, Judge0, Django and Nginx run together on the target Linux environment.
- Backup and recovery procedures have been tested.
- No critical security or data-integrity defects remain.

LABORA can be considered ready for a campus-wide rollout targeting 1,000 concurrent active users only when:

- The controlled pilot succeeds.
- Linux Judge0 sandbox limits are verified.
- Worker interruption and database restore drills pass.
- Progressive load tests reach 1,000 users on representative hardware.
- Actual measurements meet the agreed latency, error-rate, queue and resource thresholds.
- The college IT team accepts the operational runbooks and recovery process.

---

## 6. Scope boundaries

For the first production release, keep the scope focused on the existing product:

- Student, teacher and administrator workflows.
- Python, C and Java execution.
- Secure Browser integration.
- Submission/review/approval and lab records.
- Self-hosted deployment and operational reliability.

Do not add new programming languages, AI-based proctoring, paid execution APIs or unrelated features until the core system is stable, secure and measured under real usage.

---

## 7. Source files that should be treated as primary

| Concern | Primary source |
|---|---|
| Backend settings | `server/backend/labora/settings.py` |
| Execution queue | `server/backend/labs/tasks.py` |
| API and workflow logic | `server/backend/labs/views.py` |
| API data exposure | `server/backend/labs/serializers.py` |
| Database schema | `server/backend/labs/models.py`, `server/backend/accounts/models.py` |
| Backend tests | `server/backend/labs/tests.py`, `server/backend/accounts/tests.py` if present |
| Local execution | `server/backend/labs/executor.py` |
| Secure Browser signing and kiosk behavior | `Secure Browser/resources/app/main.js`, `preload.js`, `labora.config.json` |
| Production orchestration | `production_kit/docker/docker-compose.prod.yml` |
| Reverse proxy | `production_kit/nginx/nginx.conf` |
| Load test | `production_kit/load_testing/locustfile.py` |
| Deployment and recovery instructions | `production_kit/docs/`, `production_kit/scripts/` |

**Working rule:** make changes in the active source tree first, add tests, validate them, then update the production kit and evidence documents. Do not treat the `production_kit/backend_async/` copy as active runtime code unless it is deliberately integrated and tested.
