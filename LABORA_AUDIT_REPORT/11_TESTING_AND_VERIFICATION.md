# LABORA — Testing & Verification Technical Audit

**Test Runner:** Django Test Runner (`manage.py test`)  
**Test Client:** Django REST Framework `APIClient`  
**Execution Environment:** Windows Native Python `3.11.9`, GCC `16.2.0`, OpenJDK `17.0.12`  
**Actual Execution Command:** `server\backend\.venv\Scripts\python.exe server\backend\manage.py test labs`  
**Actual Runtime Test Result:** **10 TESTS PASSED (Ran in 42.863s, Exit Code: 0)**  

---

## 1. Automated Test Suite Execution Audit

During this technical audit, the test suite was executed against an isolated SQLite test database.

### Actual Command Output:
```text
Creating test database for alias 'default'...
Found 10 test(s).
System check identified no issues (0 silenced).
..........
----------------------------------------------------------------------
Ran 10 tests in 42.863s

OK
Destroying test database for alias 'default'...
```

---

## 2. Test Case Inventory & Coverage Analysis

Located in [server/backend/labs/tests.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/tests.py):

| Test Method Name | Component Under Test | Scope & Assertion Details | Runtime Result | Verified Invariants |
|---|---|---|---|---|
| `test_secure_browser_required` | `labs.secure_browser` | Asserts unsigned request to restricted practical returns HTTP 403 `secure_browser_required`. Asserts valid HMAC signature returns HTTP 200 with `secure_browser: true`. Asserts forged signature or expired timestamp returns HTTP 403. | **PASS** | HMAC attestation prevents unauthorized browser access. |
| `test_student_login_gate` | `accounts.views.login` | Enables `students_secure_browser_only=True` in `CollegeSettings`. Asserts student login without HMAC signature returns HTTP 403. Asserts student with signature returns HTTP 200. Asserts teachers are never blocked by browser gate. | **PASS** | Global Secure Browser login gate is strictly enforced. |
| `test_run_all_languages` | `labs.executor.run_local` | Runs Python (Prime check), C (Sum of N integers via GCC), and Java (Recursive factorial via OpenJDK). Asserts HTTP 200 and `status="Accepted"` with verified output string matches. | **PASS** | Compilers (GCC, Javac) and interpreters (Python) function properly in local mode. |
| `test_compile_error_reported` | `labs.executor.run_local` | Submits syntactically invalid C code (`int main( {`). Asserts `status="Compilation Error"` and compiler diagnostics captured in `compile_output`. | **PASS** | Compiler failure diagnostics are cleanly captured without crashing. |
| `test_full_flow_submit_approve_record` | Full Academic Lifecycle | End-to-end integration: 1) Workspace open -> 2) Code run -> 3) Activity telemetry flush -> 4) Final submit -> 5) Student isolation check -> 6) Teacher indicators review -> 7) Teacher approval -> 8) DOCX / PDF record export. | **PASS** | End-to-end domain lifecycle is functional and cohesive. |
| `test_correction_unlocks` | Review Workflow | Submits practical, teacher requests correction (`status="correction"`), student workspace verifies code is unlocked and allows new autosaves. | **PASS** | Correction requests correctly release submission lock. |
| `test_student_cannot_create_practical_or_see_question_directly` | RBAC Isolation | Asserts student cannot create practicals (HTTP 403) and that `GET /api/practicals/<id>/` hides question text from students. | **PASS** | Students cannot read assignment questions outside the Secure Browser workspace. |
| `test_unenrolled_student_blocked` | Course Isolation | Creates student not enrolled in MCA101. Asserts access to workspace returns HTTP 403 Forbidden. | **PASS** | Multi-tenancy course boundaries are strictly respected. |
| `test_async_execution_flow` | Celery Engine & Detail Polling | Dispatches async run via `POST /run-async/`, asserts HTTP 202 with `execution_id`, polls `GET /api/executions/<id>/`, asserts state transitions to `COMPLETED` and `Accepted`, verifies student2 cannot view student1's execution (HTTP 403), and teacher can view it (HTTP 200). | **PASS** | Celery async execution and isolation checks function properly under eager mode. |
| `test_cannot_submit_while_execution_pending` | Submission Integrity Guard | Creates an execution in `PROCESSING` state. Asserts calling `POST /submit/` returns HTTP 400 with `code: "run_required"`. | **PASS** | Pending execution prevents immediate submission when no prior accepted run exists. |

---

## 3. Test Configuration & Mocking Mechanics

### Test Suite Settings Overrides:
```python
@override_settings(CODE_EXECUTOR="local", SECURE_BROWSER_KEY=KEY, CELERY_TASK_ALWAYS_EAGER=True)
class LaboraFlowTests(TestCase):
```
- **`CELERY_TASK_ALWAYS_EAGER=True`:** Forces Celery to execute tasks synchronously within the same Python thread instead of connecting to a real Redis broker.
- **`CODE_EXECUTOR="local"`:** Forces code execution to run through `run_local` using local host compilers (`gcc`, `javac`, `python`).
- **Critical Limitation of Test Configuration:**
  - The automated test suite **does not test real Celery broker communication via Redis**.
  - The test suite **does not test Judge0 container sandboxing via REST API**.
  - All 10 tests run in a single-threaded SQLite in-memory environment, so real database concurrency and locking issues are not exercised.

---

## 4. Missing Test Scenarios

The following scenarios are completely untested in the existing automated test suite:
1. **Redis Broker Failure:** No tests simulate Redis disconnection during `workspace_run_async`.
2. **Judge0 Network Failures & Retries:** No tests assert behavior when Judge0 returns HTTP 502/503 or drops connections during result polling.
3. **Stale Execution Submission Exploit:** No test verifies what happens if a student modifies code after an accepted run and submits without running again.
4. **CSV Bulk Import Edge Cases:** `accounts/tests.py` is empty (0 test cases). CSV onboarding with malformed lines, duplicate roll numbers, or missing department codes is untested.
5. **Concurrent Database Submissions:** No multi-threaded test simulates concurrent autosaves, runs, and submits on the same submission.
6. **PDF Generation Error Fallback:** No test exercises the `ImportError` / `OSError` fallback when WeasyPrint system dependencies (Cairo/Pango) are missing.

---

## 5. Inventory of Blocked Tests

In strict accordance with the audit guidelines (*"Do not claim tests passed if they were not run. Distinguish between implemented and verified vs unknown or requires external verification"*), the following tests were **`BLOCKED`** during this audit:

### Blocked Test 1: Progressive 1,000-User Locust Load Test
- **Status:** **`BLOCKED (Requires Dedicated Server Cluster)`**
- **Technical Reason:** Simulating 1,000 concurrent students typing, autosaving, and compiling C/Java programs requires multi-core staging server hardware with dedicated CPU resources. The script is implemented in [production_kit/load_testing/locustfile.py](file:///d:/v/LABORA-Test-Windows/production_kit/load_testing/locustfile.py) but cannot be executed in this developer workspace.

### Blocked Test 2: Live Linux Kernel `cgroups` v2 Sandboxing Verification
- **Status:** **`BLOCKED (Requires Native Linux Kernel)`**
- **Technical Reason:** Verifying that Judge0 CE cleanly clamps CPU limits (5.0s), restricts memory (256MB), and terminates fork bombs requires a native Linux kernel with `cgroups` v1/v2 controller mounts.

### Blocked Test 3: Worker SIGKILL Interruption Drill
- **Status:** **`BLOCKED (Requires Live Container Stack)`**
- **Technical Reason:** Testing task recovery when a Celery worker is abruptly killed with `SIGKILL` during active Judge0 execution requires a running multi-container Docker Compose deployment.

### Blocked Test 4: Live PostgreSQL Backup & Restoration Verification
- **Status:** **`BLOCKED (Requires Live Container Stack)`**
- **Technical Reason:** Live execution of `backup_postgres.sh` and `restore_postgres.sh` requires active PostgreSQL container instances.
