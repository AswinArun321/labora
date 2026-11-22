# LABORA — Integration Report

**Document:** `production_kit/docs/INTEGRATION_REPORT.md`  
**Date:** 22 November 2026  

---

## 1. Backend & Queue Integration

* **Broker Connection:** Connected Celery 5.7 to Redis 7 via `CELERY_BROKER_URL`.
* **Task Routing:** Background task `labs.tasks.dispatch_execution_task` registered and auto-discovered.
* **Worker Execution Mode:**
  - In unit tests: `CELERY_TASK_ALWAYS_EAGER=True` executes tasks in-process for deterministic test assertion.
  - In staging/production: Celery worker processes tasks independently via `celery -A labora worker -l info --concurrency=8`.

---

## 2. API Endpoint Specifications

### 2.1. Submit Code for Asynchronous Execution
* **Endpoint:** `POST /api/workspace/<practical_id>/run-async/`
* **Permission:** `IsStudent`
* **Request Body:**
  ```json
  {
    "code": "print('Hello, world!')",
    "stdin": ""
  }
  ```
* **Response (HTTP 202 Accepted):**
  ```json
  {
    "execution_id": 42,
    "state": "QUEUED",
    "status": "In Queue",
    "created_at": "2026-11-22T12:00:00Z",
    "poll_url": "/api/executions/42/"
  }
  ```

### 2.2. Poll Execution Status & Output
* **Endpoint:** `GET /api/executions/<execution_id>/` (and alias `/api/workspace/<practical_id>/executions/<execution_id>/`)
* **Permission:** `IsAuthenticated` (Student owner or assigned teacher/admin)
* **Response while processing:**
  ```json
  {
    "id": 42,
    "state": "PROCESSING",
    "status": "In Queue",
    "is_complete": false,
    "stdout": "",
    "stderr": "",
    "compile_output": "",
    "time": "",
    "memory": null
  }
  ```
* **Response upon completion:**
  ```json
  {
    "id": 42,
    "state": "COMPLETED",
    "status": "Accepted",
    "is_complete": true,
    "stdout": "Hello, world!\n",
    "stderr": "",
    "compile_output": "",
    "time": "0.02",
    "memory": 8420
  }
  ```

---

## 3. React Frontend Integration

* **Non-Blocking UI Flow:** In `server/frontend/dist/assets/index-DRq-BgX-.js`:
  1. Student clicks **Run**. The button immediately toggles to `Running…` (`disabled: true`), preventing accidental multi-click race conditions.
  2. Any pending editor telemetry batches are flushed (`await ae()`).
  3. Client dispatches `POST /api/workspace/<id>/run-async/`.
  4. On HTTP 202 receipt, the UI displays an amber `Queued` badge and renders `[LABORA] Code queued in Celery worker... Waiting for sandbox runner...` in Monaco's output panel.
  5. The client initiates non-blocking polling to `GET /api/executions/<id>/` every 1,000ms.
  6. As the runner transitions through `DISPATCHING`, `SUBMITTED_TO_RUNNER`, and `PROCESSING`, the badge dynamically reflects intermediate states.
  7. Upon terminal resolution (`is_complete=True`), the Monaco panel renders stdout, stderr, compile errors, runtime, and memory metrics with an emerald `Accepted` badge (or rose error badge).
  8. Polling includes network-retry resilience against intermittent packet loss.
  9. A fallback to synchronous `/run/` is retained for graceful degradation.

---

## 3. Backward Compatibility & Submission Integration

* **Backward Compatibility:** Existing synchronous endpoint `POST /api/workspace/<id>/run/` was preserved unchanged.
* **Submission Safety Guard:** In `labs/views.py`:
  ```python
  last_ok = sub.executions.filter(status="Accepted", state=Execution.State.COMPLETED).order_by("-created_at").first()
  ```
  Students cannot submit while code is still `QUEUED`, `DISPATCHING`, or `PROCESSING`.
