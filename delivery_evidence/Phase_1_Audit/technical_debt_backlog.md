# Phase 1: Technical Debt Backlog & Prioritization

**Document:** Technical Debt Backlog  
**Audit Baseline:** `LABORA-Test-Windows`  

---

## 1. High Priority Debt (Must Fix for Production Scale)

* **DEBT-01: Synchronous HTTP Code Execution**
  - *Location:* `server/backend/labs/views.py` (`workspace_run`), `labs/executor.py` (`run_judge0`)
  - *Issue:* HTTP thread blocks for up to 60s while waiting for execution. 1,000 concurrent users will cause 504 timeouts.
  - *Remediation:* Deploy Celery task queue with asynchronous polling endpoints.

* **DEBT-02: Ephemeral Execution State Persistence**
  - *Location:* `server/backend/labs/models.py` (`Execution`)
  - *Issue:* Execution record is created only after execution finishes. Unfinished or crashed runs leave no audit trace.
  - *Remediation:* Create `Execution` record with status `QUEUED` prior to task dispatch; track intermediate states.

* **DEBT-03: Windows Test Environment Defect**
  - *Location:* `server/backend/labs/tests.py` (line 30)
  - *Issue:* Hardcoded `/dev/null` causes test runner failure on native Windows hosts.
  - *Remediation:* Replace `/dev/null` with `os.devnull` or `io.StringIO()` in test runner.

---

## 2. Medium Priority Debt (Operational & Scaling Hardening)

* **DEBT-04: Database Index Optimization for 1,000 Users**
  - *Location:* `server/backend/labs/models.py`
  - *Issue:* Queries on `ActivityEvent` and `Execution` will grow to millions of rows under 1,000 students.
  - *Remediation:* Add composite database indexes on `(submission, created_at)` and `(status, created_at)`.

* **DEBT-05: Missing Client Auto-Update Mechanism**
  - *Location:* `Secure Browser/`
  - *Issue:* If the shared secret key or server URL changes, each lab computer must be manually reconfigured.
  - *Remediation:* Add an auto-update manifest check in `Secure Browser/resources/app/main.js` on startup.

* **DEBT-06: Production Container Orchestration Gaps**
  - *Location:* Workspace root
  - *Issue:* Project ships with Windows `.bat` launchers only; missing Linux deployment assets.
  - *Remediation:* Integrate the container stack from `production_kit/docker/`.

---

## 3. Low Priority Debt (Cleanup & Optimization)

* **DEBT-07: Unused AI Review Code in First Release**
  - *Location:* `server/backend/labs/ai_review.py`
  - *Issue:* Excluded by scope decisions (`plann.md` Section 2.1).
  - *Remediation:* Disable AI endpoints in production release to eliminate attack surface and external dependencies.
