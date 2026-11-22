# LABORA — Test Execution Report

**Document:** `production_kit/docs/TEST_REPORT.md`  
**Date:** 22 November 2026  
**Test Runner:** Django `manage.py test`  
**Platform:** Python 3.11.9, GCC 16.2.0, OpenJDK 17.0.12  

---

## 1. Automated Test Suite Results

```text
Creating test database for alias 'default'...
Found 10 test(s).
System check identified no issues (0 silenced).
..........
----------------------------------------------------------------------
Ran 10 tests in 42.357s

OK
Destroying test database for alias 'default'...
```

---

## 2. Test Case Breakdown & Verifications

| Test Case | Scope | Execution Result | Verification Details |
|---|---|---|---|
| `test_secure_browser_required` | Security & HMAC Attestation | **PASS** | Asserts unsigned request receives HTTP 403; valid HMAC signature receives HTTP 200; tampered/stale signature rejected. |
| `test_student_login_gate` | Security & Login Lockdown | **PASS** | Asserts student cannot login from standard browser when `students_secure_browser_only=True`; teachers remain unblocked. |
| `test_run_all_languages` | Language Compilation & Execution | **PASS** | Tests Python (Prime check), C (Sum of N integers via GCC), and Java (Recursive factorial via OpenJDK). All return status "Accepted". |
| `test_compile_error_reported` | Error Capture | **PASS** | Syntax error in C code captured cleanly with status "Compilation Error" and compiler diagnostics. |
| `test_full_flow_submit_approve_record` | End-to-End Workflow | **PASS** | Tests entire academic lifecycle: workspace load -> code execution -> event telemetry -> submission -> teacher review -> approval -> DOCX and PDF generation. |
| `test_correction_unlocks` | Review Workflow | **PASS** | Asserts teacher correction request transitions status to "correction" and unlocks student editing. |
| `test_student_cannot_create_practical` | Authorization Isolation | **PASS** | Asserts student cannot create practicals or view unreleased question text. |
| `test_unenrolled_student_blocked` | Multi-Tenancy Isolation | **PASS** | Asserts student not enrolled in a subject cannot access workspace. |
| `test_async_execution_flow` | **Asynchronous Execution Engine** | **PASS** | **Validates Priority 1:** Calls `/run-async/`, receives HTTP 202 and `QUEUED` state, Celery task executes, state transitions to `COMPLETED` / `Accepted`, and output is verified. |
| `test_cannot_submit_while_execution_pending` | **Submission Integrity Guard** | **PASS** | **Validates Priority 5:** Asserts student cannot submit while an execution is in `PROCESSING` state. Returns HTTP 400 with `code: "run_required"`. |
