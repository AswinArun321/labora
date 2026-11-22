# Phase 1: Test Baseline Verification Report

**Document:** Baseline Test Execution Report  
**Environment:** Windows 11, Python 3.11.9, GCC 16.2.0, OpenJDK 17.0.12  
**Target:** `server/backend/labs/tests.py`  

---

## 1. Test Suite Execution Analysis

When running the existing Django test suite:
```powershell
cd server\backend
.\.venv\Scripts\python.exe manage.py test
```

### Findings
The test suite discovered 8 integration test cases in `labs.tests.LaboraFlowTests`:
1. `test_secure_browser_required` — Validates HMAC signature validation, replay protection, and rejection of normal browsers.
2. `test_student_login_gate` — Tests `students_secure_browser_only` restriction.
3. `test_run_all_languages` — Tests execution of Python, C, and Java programs.
4. `test_compile_error_reported` — Tests error reporting when C code has syntax errors.
5. `test_full_flow_submit_approve_record` — Tests full lifecycle: workspace load -> run -> event tracking -> submission -> teacher review -> approval -> DOCX/PDF generation.
6. `test_correction_unlocks` — Tests that teacher correction requests unlock the student editor.
7. `test_student_cannot_create_practical_or_see_question_directly` — Tests permission isolation.
8. `test_unenrolled_student_blocked` — Tests that unenrolled students cannot access workspace.

### Environmental Failure Discovered
During test `setUp`:
```python
call_command("seed_demo", stdout=open("/dev/null", "w"))
```
On Windows, `open("/dev/null", "w")` raises `FileNotFoundError: [Errno 2] No such file or directory: '/dev/null'`.

### Verification on Linux / With Cross-Platform Fix
When running on Linux or when redirecting output cross-platform:
```python
import os
call_command("seed_demo", stdout=open(os.devnull, "w"))
```
All 8 integration tests execute and pass cleanly.

---

## 2. Test Verification Matrix

| Test Case | Functional Scope | Baseline Status | Remediated Status |
|---|---|---|---|
| `test_secure_browser_required` | HMAC Signature & Skew Verification | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_student_login_gate` | Secure Browser Login Restriction | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_run_all_languages` | Python, C, and Java Execution | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_compile_error_reported` | C Compilation Error Capture | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_full_flow_submit_approve_record` | End-to-End Exam & Record Flow | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_correction_unlocks` | Correction Workflow & State Unlock | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_student_cannot_create_practical` | Teacher Privilege Isolation | Failed on Win `/dev/null` | **PASS (100%)** |
| `test_unenrolled_student_blocked` | Student Enrollment Isolation | Failed on Win `/dev/null` | **PASS (100%)** |
