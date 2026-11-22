# LABORA — Prioritized Technical Debt, Defects & Bug Inventory

**Audit Scope:** Full repository code inspection  
**Prioritization Standards:** Critical (P0) > High (P1) > Medium (P2) > Low (P3)  

---

## 1. Defect & Technical Debt Inventory

### DEBT-01: Celery Worker Saturated by Synchronous Judge0 Polling Loop
- **Severity:** **CRITICAL (P0)**
- **Affected File:** [server/backend/labs/tasks.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/tasks.py#L122-L166) (`dispatch_execution_task`)
- **Explanation:** In `labs/tasks.py`, after dispatching code to Judge0, the Celery task loops `while time.time() - start_time < max_wait_seconds:` with `time.sleep(poll_interval)`. During this sleep, the Celery worker process is blocked and cannot process any other queued tasks.
- **Impact:** With the default production worker concurrency of 8, **only 8 simultaneous executions will completely saturate the Celery cluster**. Additional executions queue in Redis. Under exam conditions (hundreds of students running code), execution queue times exceed the 60-second frontend timeout, causing widespread test timeouts.
- **Recommended Solution:** Decouple dispatch from polling:
  1. Configure Judge0 callback webhooks (`callback_url`), or
  2. Implement an asynchronous polling task that reschedules itself using Celery countdowns/ETAs without holding a thread asleep.
- **Dependencies:** Judge0 networking reachable from backend.
- **Verification Method:** Run a Locust test with 50 concurrent executions and assert that queue wait time remains under 2 seconds.

---

### DEBT-02: Missing Original React Frontend Source Code
- **Severity:** **CRITICAL (P0)**
- **Affected File:** [server/frontend/dist/](file:///d:/v/LABORA-Test-Windows/server/frontend/dist/)
- **Explanation:** The original uncompiled React source code (`src/`, components, package.json) is missing from the repository and Git history. Modifications (such as commit `c5ab27a`) were performed by manually patching minified JavaScript in `dist/assets/index-DRq-BgX-.js`.
- **Impact:** Long-term development, UI enhancements, bug fixes, and library upgrades are extremely difficult and error-prone without the original source code.
- **Recommended Solution:** Reconstruct the frontend in a dedicated `frontend/` directory using Vite + React + TypeScript, implementing the documented API contracts in `07_API_DOCUMENTATION.md`.
- **Dependencies:** Complete API inventory (provided in this audit).
- **Verification Method:** Build frontend with `npm run build` and assert all 10 page routes render identically to the compiled distribution bundle.

---

### DEBT-03: Stale Execution Reuse in Final Submission Validation
- **Severity:** **HIGH (P1)**
- **Affected File:** [server/backend/labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py#L312-L318) (`workspace_submit`)
- **Explanation:** `workspace_submit` queries:
  `last_ok = sub.executions.filter(status="Accepted", state=Execution.State.COMPLETED).order_by("-created_at").first()`
  `if not last_ok or last_ok.code != code: return Response(..., status=400)`
  If a student ran code `A` successfully earlier, then modified code to `B` (which failed compilation or runtime), and then restored code `A` without re-running it, `last_ok` picks up the older execution. Furthermore, if an execution is currently in flight (`state=PROCESSING`) with different stdin, the stale accepted run is attached to `sub.record_execution`.
- **Impact:** Students can submit programs without proving that their current program and current standard input pass in the active session.
- **Recommended Solution:** Query the absolute latest execution for the submission:
  ```python
  latest = sub.executions.order_by("-created_at").first()
  if not latest or latest.code != code or latest.status != "Accepted" or latest.state != Execution.State.COMPLETED:
      return Response({"detail": "You must run your final code successfully before submitting.", "code": "run_required"}, status=400)
  ```
- **Dependencies:** None.
- **Verification Method:** Automated unit test asserting that modifying code, having a run fail, and reverting code requires a re-run before submitting.

---

### DEBT-04: Cleartext Shared Secret & Insecure Dev Mode in Electron Client
- **Severity:** **HIGH (P1)**
- **Affected File:** [Secure Browser/labora.config.json](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/labora.config.json#L3), [Secure Browser/resources/app/main.js](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/main.js#L20)
- **Explanation:** The HMAC key is stored in plain JSON next to the executable, and passing `--dev` completely disables kiosk and security restrictions.
- **Impact:** Students can easily extract the key or launch with `--dev` to bypass all Secure Browser protections.
- **Recommended Solution:**
  1. Strip `--dev` flag handling from packaged production builds.
  2. Protect `labora.config.json` via OS-level filesystem ACLs on institutional PCs.
  3. Explore asymmetric machine-level device attestation.
- **Dependencies:** Electron packaging scripts.
- **Verification Method:** Launch packaged browser with `--dev` and assert kiosk mode remains strictly locked.

---

### DEBT-05: Sensitive Judge0 Internal Tokens Leaked in API Responses
- **Severity:** **HIGH (P1)**
- **Affected File:** [server/backend/labs/serializers.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/serializers.py#L31) (`ExecutionSerializer`)
- **Explanation:** `ExecutionSerializer` explicitly serializes `judge0_token` to students polling `GET /api/executions/<id>/`.
- **Impact:** Exposes internal infrastructure identifiers to end-users, enabling unauthorized polling or tampering if Judge0 is reachable.
- **Recommended Solution:** Remove `judge0_token` from `ExecutionSerializer.Meta.fields`.
- **Dependencies:** None.
- **Verification Method:** Inspect JSON response from `GET /api/executions/<id>/` and assert `judge0_token` is absent.

---

### DEBT-06: Production Docker Compose & Nginx Boot Failures
- **Severity:** **HIGH (P1)**
- **Affected File:** [production_kit/docker/docker-compose.prod.yml](file:///d:/v/LABORA-Test-Windows/production_kit/docker/docker-compose.prod.yml), [production_kit/nginx/nginx.conf](file:///d:/v/LABORA-Test-Windows/production_kit/nginx/nginx.conf)
- **Explanation:** Nginx requires SSL certs that do not exist on initial boot; Judge0 container lacks `privileged: true` and `/sys/fs/cgroup` mounts; Django backend lacks an automated startup migration script.
- **Impact:** The production Docker stack fails to boot cleanly on a new server.
- **Recommended Solution:**
  1. Add an entrypoint script to `Dockerfile.backend` running `migrate` and `collectstatic`.
  2. Add `privileged: true` and `/sys/fs/cgroup:/sys/fs/cgroup:ro` to `judge0-server`.
  3. Provide an initial HTTP-only bootstrap Nginx configuration for ACME/Certbot issuance.
- **Dependencies:** Staging Linux server.
- **Verification Method:** Run `docker compose -f docker-compose.prod.yml up -d` on a fresh VM and assert all containers reach healthy status.

---

### DEBT-07: Missing Database Indexes on High-Volume Telemetry Tables
- **Severity:** **MEDIUM (P2)**
- **Affected File:** [server/backend/labs/models.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/models.py) (`ActivityEvent`, `Submission`, `Execution`)
- **Explanation:** Missing composite indexes on `labs_activityevent(submission_id, created_at)` and `labs_execution(submission_id, status, state, created_at)`.
- **Impact:** At 1,000 active students, telemetry tables will grow to millions of rows, causing slow teacher dashboards and database CPU spikes.
- **Recommended Solution:** Add `indexes = [models.Index(fields=['submission', 'created_at'])]` to `ActivityEvent.Meta` and create a Django migration.
- **Dependencies:** None.
- **Verification Method:** Inspect PostgreSQL `EXPLAIN ANALYZE` for submission timeline queries.

---

### DEBT-08: N+1 Query in Teacher Submissions Dashboard
- **Severity:** **MEDIUM (P2)**
- **Affected File:** [server/backend/labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py#L137-L157) (`submissions`)
- **Explanation:** In `PracticalViewSet.submissions`, `compute_indicators()` invokes `sub.versions.filter(...)`, bypassing Django's prefetch cache and triggering a separate SQL query for every student.
- **Impact:** 60–100 distinct SQL queries per dashboard load; blocks Gunicorn workers under load.
- **Recommended Solution:** Filter the prefetched `sub.versions.all()` list in Python memory using list comprehensions.
- **Dependencies:** None.
- **Verification Method:** Use `django-debug-toolbar` or `connection.queries` in unit test to assert query count is under 5.

---

### DEBT-09: Unsafe Development Defaults Permitted in Production Settings
- **Severity:** **MEDIUM (P2)**
- **Affected File:** [server/backend/labora/settings.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/settings.py)
- **Explanation:** `CODE_EXECUTOR` can be set to `"local"` even when `DEBUG=False`, and `DJANGO_SECRET_KEY` falls back to an insecure default.
- **Impact:** Accidental deployment misconfiguration leads to host RCE and session hijacking.
- **Recommended Solution:** Raise `ImproperlyConfigured` on startup if `DEBUG=False` and insecure settings are detected.
- **Dependencies:** None.
- **Verification Method:** Run `python manage.py check --deploy` and assert failure when insecure defaults are present.
