# Phase 9: Security Vulnerability & Hardening Test Report

**Document:** Security Testing Report  
**Date:** 22 November 2026  
**Scope:** OWASP Top 10, Sandboxing, HMAC Verification, and RBAC Isolation  

---

## 1. Security Test Matrix & Verification Outcomes

| Vulnerability Category | Specific Attack Vector Tested | Defense Mechanism | Test Status |
|---|---|---|---|
| **Authentication Bypass** | Direct access to `/api/workspace/<id>/` without JWT | DRF `IsAuthenticated` | **BLOCKED (HTTP 401)** |
| **Cross-Tenant Access** | Student A accessing Student B's submissions | Object-level permission check | **BLOCKED (HTTP 403)** |
| **Unenrolled Access** | Student accessing practical of subject not enrolled in | `get_student_practical` query check | **BLOCKED (HTTP 403)** |
| **HMAC Tampering** | Modifying URL path with stale HMAC signature | Constant-time HMAC comparison | **BLOCKED (HTTP 403)** |
| **HMAC Replay Attack** | Replaying signed request after 301 seconds | `SECURE_BROWSER_MAX_SKEW_SECONDS` | **BLOCKED (HTTP 403)** |
| **Post-Submission Tampering**| Modifying code after submission has been submitted | `ensure_editable` state guard | **BLOCKED (HTTP 403)** |
| **Infinite Loop / DoS** | Student program: `while True: pass` | Judge0 `CPU_TIME_LIMIT=5.0` | **TERMINATED (Time Limit Exceeded)** |
| **Fork Bomb / Process Exhaustion** | Student program: `while(1) fork();` | Judge0 `MAX_PROCESSES=60` | **CONTAINED (Runtime Error)** |
| **Memory Exhaustion** | Student program allocating 10GB array | Judge0 `MEMORY_LIMIT=256MB` | **CONTAINED (Memory Limit Exceeded)** |
| **Arbitrary File Access**| Student code reading `/etc/shadow` or `db.sqlite3` | Sandbox chroot/cgroups isolation | **BLOCKED (Permission Denied)** |

---

## 2. Hardening Sign-Off

The system enforces robust defense-in-depth:
1. Application layer: Django RBAC, JWT, and HMAC request signing.
2. Transport layer: TLS 1.2/1.3 and rate limiting.
3. Execution layer: Linux cgroups, seccomp, and CPU/memory boundaries inside Judge0.
