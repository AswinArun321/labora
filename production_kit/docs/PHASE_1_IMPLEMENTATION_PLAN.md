# LABORA — Phase 1 Asynchronous Execution Implementation Plan

**Document:** `production_kit/docs/PHASE_1_IMPLEMENTATION_PLAN.md`  
**Author:** Senior Software Architect & Backend Engineer  
**Date:** 22 November 2026  
**Git Branch:** `production-integration`  
**Target:** Safe, backward-compatible integration of asynchronous code execution for up to 1,000 concurrent active users.  

---

## 1. Initial Source Audit Verification & Findings Summary

As documented in `production_kit/docs/SOURCE_AUDIT_INITIAL.md`, direct inspection of the codebase has confirmed:

1. **Synchronous Execution Bottleneck:** In `server/backend/labs/views.py` (`workspace_run`), requests synchronously block the Python thread while calling `run_code(p.language, code, stdin)`. In `server/backend/labs/executor.py` (`run_judge0`), it posts to Judge0 with `wait=true` and a 60-second HTTP timeout. Under concurrent lab exam conditions, 50–100 simultaneous requests exhaust all WSGI/Gunicorn workers, causing HTTP 504 Gateway Timeouts.
2. **Missing Intermediate Execution States:** In `server/backend/labs/models.py`, `Execution` records are created **only after** execution returns. If an execution request times out or worker crashes mid-flight, no record is saved in the database.
3. **Frontend Coupling:** The React SPA (`server/frontend/dist/assets/index-DRq-BgX-.js`) contains an asynchronous handler `ce` that awaits `POST /api/workspace/<id>/run/` and sets `last_execution` immediately upon resolution. The submit button is gated on `last_execution?.status === 'Accepted'`.
4. **Test Suite Defect on Windows:** In `server/backend/labs/tests.py` line 30, `call_command("seed_demo", stdout=open("/dev/null", "w"))` fails on Windows hosts with `FileNotFoundError: [Errno 2] No such file or directory: '/dev/null'`.

---

## 2. Identified Incompatibilities & Missing Integration Points

| # | Component | Existing / Template State | Missing Integration / Defect | Required Engineering Action |
|---|---|---|---|---|
| **1** | **`Execution` Model** | Only has `code`, `stdin`, `stdout`, `stderr`, `compile_output`, `status`, `time`, `memory`, `created_at`. | Missing `judge0_token`, `runner_url`, `last_error`, `started_at`, `completed_at`, `retry_count`, and execution state choices. | Update `labs/models.py` with non-breaking nullable fields and generate Django migration `0002_*.py`. |
| **2** | **Celery Integration** | Celery template exists only in `production_kit/backend_async/celery.py`. `server/backend/labora/__init__.py` is empty (0 bytes). | Django does not load or discover Celery tasks on startup. | Add `celery.py` to `server/backend/labora/` and initialize in `labora/__init__.py`. |
| **3** | **Execution Tasks** | Celery tasks reside outside the Django app in `production_kit/backend_async/tasks.py`. | Tasks are not in the Django app autodiscovery path (`labs.tasks`). | Integrate production Celery tasks cleanly into `server/backend/labs/tasks.py`. |
| **4** | **API Routing** | `urls.py` only routes synchronous `/api/workspace/<id>/run/`. | Missing `POST /api/workspace/<id>/run-async/` and `GET /api/executions/<id>/` as mandated by spec. | Add both routes to `server/backend/labora/urls.py` while retaining existing `/run/` for backward compatibility. |
| **5** | **Execution State Machine** | Only stores final string (`Accepted`, `Compilation Error`, etc.). | Spec requires 8 distinct lifecycle states: `QUEUED`, `DISPATCHING`, `SUBMITTED_TO_RUNNER`, `PROCESSING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`. | Implement two-tiered status tracking: `state` (lifecycle) and `status` (Judge0 result). Map Judge0 results cleanly. |
| **6** | **Settings Configuration** | `server/backend/labora/settings.py` has Judge0 settings but no Celery/Redis settings. | Celery defaults to local memory broker without Redis configuration. | Add `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_TIME_LIMIT`, and worker concurrency settings to `settings.py`. |
| **7** | **Windows Test Runner Defect** | `server/backend/labs/tests.py` line 30 opens `/dev/null`. | Crashes on native Windows environments with `FileNotFoundError`. | Replace `/dev/null` with `os.devnull` (cross-platform safe). |

---

## 3. Exact List of Files to Change & Rationale

```
server/backend/
├── labora/
│   ├── __init__.py                # Import celery_app so Celery is shared across Django
│   ├── celery.py                  # [NEW] Celery application configuration & broker settings
│   ├── settings.py                # Add Celery/Redis configuration variables
│   └── urls.py                    # Add run-async/ and executions/<id>/ routes
│
└── labs/
    ├── models.py                  # Add asynchronous tracking fields to Execution model
    ├── migrations/
    │   └── 0002_execution_async.py# [NEW] Database migration for new Execution fields
    ├── tasks.py                   # [NEW] Celery background task dispatching to Judge0/local runner
    ├── views.py                   # Add workspace_run_async and execution_detail endpoints
    ├── serializers.py             # Enhance ExecutionSerializer with state, token, timestamps
    └── tests.py                   # Fix /dev/null defect & add comprehensive async execution tests
```

### Detailed File Changes

#### 1. `server/backend/labs/models.py`
* **Why:** The `Execution` model needs to persist execution lifecycle state from the moment the student clicks Run (`QUEUED`), before any background worker picks it up.
* **Fields to Add:**
  - `state`: CharField (`QUEUED`, `DISPATCHING`, `SUBMITTED_TO_RUNNER`, `PROCESSING`, `COMPLETED`, `FAILED`, `TIMED_OUT`, `CANCELLED`) with default `QUEUED`.
  - `judge0_token`: CharField(max_length=64, blank=True, null=True, db_index=True).
  - `runner_url`: CharField(max_length=200, blank=True).
  - `started_at`: DateTimeField(null=True, blank=True).
  - `completed_at`: DateTimeField(null=True, blank=True).
  - `last_error`: TextField(blank=True).
  - `retry_count`: PositiveSmallIntegerField(default=0).
* **Backward Compatibility:** All existing fields (`code`, `stdin`, `stdout`, `stderr`, `compile_output`, `status`, `time`, `memory`, `created_at`) and relationships are 100% preserved. Existing queries and submission relationships continue to work without modification.

#### 2. `server/backend/labs/migrations/0002_execution_async.py`
* **Why:** Django requires a migration to apply new schema fields to PostgreSQL and SQLite databases safely.
* **Content:** Standard Django migration adding the new fields with appropriate defaults and nullability.

#### 3. `server/backend/labora/celery.py`
* **Why:** Provides the central Celery application instance configured to read from `django.conf:settings` with namespace `CELERY_`.
* **Content:** Standard Celery 5.x app initialization with auto-discovery, time limits (120s), and fair prefetch.

#### 4. `server/backend/labora/__init__.py`
* **Why:** Ensures `@shared_task` decorators in Django apps bind to the instantiated Celery app when Django loads.
* **Content:** `from .celery import app as celery_app; __all__ = ("celery_app",)`

#### 5. `server/backend/labora/settings.py`
* **Why:** Connects Django and Celery to Redis and defines worker task parameters.
* **Content:** Adds `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_TRACK_STARTED`, `CELERY_TASK_TIME_LIMIT`, and `CELERY_TASK_ALWAYS_EAGER` (for synchronous unit testing).

#### 6. `server/backend/labs/tasks.py`
* **Why:** Executes untrusted code in the background without blocking Django web request threads.
* **Content:** `dispatch_execution_task(execution_id)`:
  - Fetches `Execution` record, sets `state="DISPATCHING"`.
  - If `CODE_EXECUTOR == "judge0"`: sends async submission to Judge0 (`wait=false`), stores token and runner URL, transitions to `SUBMITTED_TO_RUNNER` and `PROCESSING`, polls until finished, parses result, updates `state="COMPLETED"` (or `FAILED`/`TIMED_OUT`), and sets `completed_at`.
  - If `CODE_EXECUTOR == "local"`: executes via safe subprocess runner in temporary directory, updates record.
  - Automatically emits `ActivityEvent(kind="run")` upon completion.

#### 7. `server/backend/labs/serializers.py`
* **Why:** Exposes the new asynchronous execution state, timestamps, and error fields to client API consumers.
* **Content:** Extend `ExecutionSerializer` to include `state`, `is_complete`, `created_at`, `started_at`, `completed_at`, `last_error`.

#### 8. `server/backend/labs/views.py`
* **Why:** Provides the two mandatory endpoints specified in Priority 1 and ensures the submission workflow checks execution completion.
* **Content:**
  - `workspace_run_async`: Non-blocking endpoint. Creates `Execution` with `state="QUEUED"`, triggers `dispatch_execution_task.delay(ex.id)`, and immediately returns HTTP 202 with `{"execution_id": ex.id, "state": "QUEUED"}`.
  - `execution_detail`: Endpoint `GET /api/executions/<id>/` returning current execution status, stdout, stderr, compile output, time, memory, and completion flag. Strictly enforces student ownership (`ex.submission.student == request.user`) or teacher permission.
  - Retain `workspace_run` for complete backward compatibility.

#### 9. `server/backend/labora/urls.py`
* **Why:** Routes the new endpoints to their view functions.
* **Content:**
  - `path("workspace/<int:practical_id>/run-async/", labs.workspace_run_async)`
  - `path("executions/<int:pk>/", labs.execution_detail)`

#### 10. `server/backend/labs/tests.py`
* **Why:** Fix the `/dev/null` Windows test runner defect and validate the entire asynchronous execution workflow with automated unit and integration tests.
* **Content:**
  - Fix `open("/dev/null", "w")` -> `open(os.devnull, "w")`.
  - Add `test_async_run_queued_and_completed`: Tests `POST /run-async/` returns 202, execution record is created with `QUEUED`, task executes, and status transitions to `COMPLETED` / `Accepted`.
  - Add `test_execution_detail_permission`: Asserts student B cannot inspect student A's execution.
  - Add `test_cannot_submit_while_execution_pending`: Verifies submission is blocked if execution is not yet completed and Accepted.

---

## 4. Implementation Phasing Sequence

1. **Phase 1A: Database Schema & Migration** — Update `labs/models.py` and run `manage.py makemigrations`.
2. **Phase 1B: Celery Configuration** — Add `labora/celery.py`, update `labora/__init__.py`, update `labora/settings.py`.
3. **Phase 1C: Background Tasks & Asynchronous Views** — Add `labs/tasks.py`, implement views in `labs/views.py`, register URLs in `labora/urls.py`, update serializers.
4. **Phase 1D: Automated Test Verification** — Fix `/dev/null` defect in `labs/tests.py`, add async execution tests, run full test suite with `.venv\Scripts\python.exe manage.py test`.
5. **Phase 1E: Integration & Audit Documentation** — Document exact code changes, test results, and update deliverables in `production_kit/docs/`.
