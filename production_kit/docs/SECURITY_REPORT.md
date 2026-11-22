# LABORA — Production Security Report

**Document:** `production_kit/docs/SECURITY_REPORT.md`  
**Date:** 22 November 2026  
**Auditor:** Application Security Engineer  

---

## 1. Threat Modeling & Security Posture

### 1.1. Untrusted Code Execution Boundary
* **Production Sandbox:** Student code executes inside self-hosted Judge0 CE containers using Linux `cgroups` (CPU and RAM limits) and `seccomp` filters.
* **Network Isolation:** The Judge0 execution pool resides on an isolated Docker bridge network (`judge0-net`) with outbound internet disabled. Untrusted code cannot contact campus internal systems or LAN assets.
* **Resource Clamping:** CPU time limit (5.0s), wall clock limit (10.0s), RAM limit (256MB), process count limit (max 60 threads). Fork bombs and infinite loops are safely contained.
* **Prohibition of Local Runner:** In production, `CODE_EXECUTOR=local` must be disabled.

### 1.2. Client Attestation & HMAC Request Signing Assessment
* **Current Design:** The Electron client hashes `(timestamp, method, path)` with a shared key `LABORA_SECURE_BROWSER_KEY` using HMAC-SHA256.
* **Security Assessment:** As noted in Priority 7, a shared key embedded in distributed client binaries cannot be treated as an unextractable hardware secret. A sophisticated attacker with local administrator access can extract the key from memory.
* **Defense-in-Depth Mitigation:**
  1. The HMAC signature defeats casual web browser access, automated curl scripts, and standard proxy injection.
  2. Physical lab invigilation remains the primary defense against physical tampering.
  3. All academic authorizations (subject enrollment, exam time windows, lock states) are strictly enforced on the server side.
  4. Granular typing telemetry and background process audits are logged immutably for teacher review.

### 1.3. Multi-Tenant Data Isolation
* Object-level permission checks verified on all submission, version, and execution endpoints.
* Cross-student data inspection returns HTTP 403 Forbidden.
* Submissions are immutably locked upon submit; unauthorized post-submission edits are blocked.
