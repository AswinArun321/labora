# LABORA — Security Verification & Vulnerability Audit Results

**Document:** `production_kit/docs/SECURITY_VERIFICATION_RESULTS.md`  
**Date:** 22 November 2026  
**Auditor:** Application Security Engineer & Software Architect  

---

## 1. Security Audit Matrix

| Security Domain | Inspection Focus | Audit Status | Findings, Mitigations & Evidence |
|---|---|---|---|
| **1. Authentication & JWT** | Login, token issuance, refresh, and session expiration. | **`VERIFIED`** | `SimpleJWT` with 60m access and 7d refresh. Authenticated in `manage.py test` and live server boot. |
| **2. Role-Based Access Control** | Student, Teacher, and Administrator permission enforcement. | **`VERIFIED`** | `test_student_cannot_create_practical` and `test_correction_unlocks` pass. Students cannot publish practicals or approve grades. |
| **3. Multi-Tenant Student Isolation** | Cross-student code inspection, submission tampering, execution leakage. | **`VERIFIED`** | `test_unenrolled_student_blocked` passes. `labs/views.py` enforces ownership (`ex.submission.student == request.user`) returning HTTP 403. |
| **4. Electron Secure Browser HMAC** | Shared HMAC-SHA256 request signing and replay prevention. | **`VERIFIED`** | `test_secure_browser_required` passes. Unsigned, tampered, or expired timestamps (>120s) rejected with HTTP 403. |
| **5. Embedded Secret Threat Model** | Risk of extracted HMAC key from Electron client binary. | **`VERIFIED (DOCUMENTED)`** | Assessed: Shared key embedded in client binary is not hardware attestation. Mitigated via defense-in-depth: physical invigilation, server-side RBAC, and granular immutable audit logs. |
| **6. Untrusted Code Isolation** | Preventing student programs from compromising host server or LAN. | **`VERIFIED (CONFIG)`** | Configured Judge0 CE on isolated bridge `judge0-net` with `internal: true` (no outbound internet routing). Local executor rejected in production. |
| **7. Resource Exhaustion Clamping**| Protection against infinite loops, fork bombs, and memory bombs. | **`VERIFIED`** | Real infinite loop tested: terminated with `Time Limit Exceeded`. Judge0 cgroups config clamps CPU (5s), RAM (256MB), and processes (60). |
| **8. API Rate Limiting** | Denial-of-service and brute force protection. | **`VERIFIED`** | Nginx configured with IP-based limits for login (`30r/m`) and JWT token-based limits (`$client_id`) for execution (`60r/m`), preventing NAT throttling in computer labs. |
| **9. Secrets & Credential Management** | Preventing hardcoded secrets and environment variable leakage. | **`VERIFIED`** | Inspected `settings.py` and `docker-compose.prod.yml`. All secrets read from environment variables; production deployment guide enforces `openssl rand -hex` secrets. |
| **10. SQL Injection & XSS** | Parameterized queries, ORM sanitization, and React output escaping. | **`VERIFIED`** | Django ORM parameterized queries used exclusively; Monaco output rendered as text nodes inside `<pre>`, preventing XSS injection. |
| **11. Database & Backup Security**| File permissions, backup encryption, and database exposure. | **`VERIFIED`** | PostgreSQL port 5432 bound exclusively to private internal network `labora-internal` (not exposed on host). Backup scripts store dumps with 0600 permissions. |

---

## 2. In-Depth Analysis: Electron Secure Browser Threat Model

### The Vulnerability:
The Electron Secure Browser embeds a shared HMAC secret key:
`LABORA_SECURE_BROWSER_KEY`

Every outgoing HTTP request generates:
`X-Labora-Signature = HMAC-SHA256(key, timestamp + method + path)`

### Risk Assessment:
In a client-server architecture, any secret embedded inside client binaries distributed to untrusted hardware (e.g. students' personal laptops or compromised lab PCs) can theoretically be extracted from memory or reverse-engineered by a skilled attacker with root/administrator access. Therefore, **the client binary alone cannot be treated as mathematical proof that the environment is secure or cheat-proof**.

### Defense-in-Depth Security Posture:
1. **Deterrence of Casual Abuse:** The HMAC signature effectively defeats casual web browsers, automated curl/Postman scripts, and off-the-shelf HTTP proxies.
2. **Physical Lab Invigilation:** Real examinations must take place inside physical college computer labs under active teacher invigilation.
3. **Immutable Server Telemetry:** Every keystroke burst, focus loss event, external paste attempt, and drag-and-drop block is recorded on the server as an immutable `ActivityEvent`. Even if a client bypasses the kiosk, the absence of human typing cadence or abnormal focus telemetry flags the submission for teacher inspection.
4. **Authoritative Server Guards:** Practical lock state, time windows, and submission gating are strictly enforced on PostgreSQL, independent of client assertions.
