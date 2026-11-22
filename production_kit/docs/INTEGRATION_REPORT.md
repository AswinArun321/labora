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
* **Endpoint:** `GET /api/executions/<execution_id>/`
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

## 3. Backward Compatibility & Submission Integration

* **Backward Compatibility:** Existing synchronous endpoint `POST /api/workspace/<id>/run/` was preserved unchanged.
* **Submission Safety Guard:** In `labs/views.py`:
  ```python
  last_ok = sub.executions.filter(status="Accepted", state=Execution.State.COMPLETED).order_by("-created_at").first()
  ```
  Students cannot submit while code is still `QUEUED`, `DISPATCHING`, or `PROCESSING`.
