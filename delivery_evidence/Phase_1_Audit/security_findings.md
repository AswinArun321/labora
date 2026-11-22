# Phase 1: Security Findings & Threat Analysis

**Document:** Security Findings Report  
**Date:** 22 November 2026  
**Audited System:** LABORA Core & Secure Browser  

---

## 1. Security Strengths Identified

1. **Browser Exam Key (Cryptographic Request Signing):**
   - Implemented in `Secure Browser/resources/app/main.js` and verified in `labs/secure_browser.py`.
   - Injects `X-Labora-Ts` and `X-Labora-Signature` (HMAC-SHA256) on all API requests.
   - Enforces a 300-second maximum clock skew to defeat replay attacks.
   - Practicals marked `require_secure_browser` strictly reject normal browsers (Chrome/Firefox/curl).

2. **Electron Hardening & Kiosk Protection:**
   - Kiosk and fullscreen mode permanently locked unless `--dev` flag is explicitly passed.
   - `setContentProtection(true)` activates hardware-level protection against OS-level screen capture / broadcasting.
   - Intercepts and swallows common escape key sequences (F5, F11, F12, Ctrl+W, Ctrl+Q, Alt+F4).
   - Blocks unauthorized navigation, popup windows, context menus, and webviews.
   - Automatically sanitizes the system clipboard on window blur, focus, and exit.

3. **Untrusted Code Execution Isolation (Production Model):**
   - Architecture delegates untrusted student code to Judge0 running in isolated Linux cgroups/seccomp containers.
   - Host server files, database credentials, and secret keys are never exposed to student code.

4. **Role-Based & Object-Level Access Control:**
   - Strict validation ensures students can only view or execute their own assignments.
   - Submissions are immutably locked upon submit; unauthorized edits post-submission are impossible.
   - Official records strictly pull execution outputs from verified database runs, preventing output fabrication.

---

## 2. Security Risks & Gaps to Remediate for Production

| Risk ID | Severity | Component | Finding & Vulnerability | Remediation |
|---|---|---|---|---|
| **SEC-01** | **CRITICAL** | `executor.py` | Local development mode (`CODE_EXECUTOR=local`) invokes `subprocess.run` on the host OS without sandbox isolation. | Strictly mandate `CODE_EXECUTOR=judge0` in production. Forbid `local` mode on production servers. |
| **SEC-02** | **HIGH** | `labora.config.json` | Default shared browser secret key (`change-this-shared-browser-key`) is present in source files. | Generate a unique 256-bit cryptographically secure key upon college deployment; inject via environment. |
| **SEC-03** | **MEDIUM** | `Secure Browser` | Binary `LABORA Secure Browser.exe` is currently unsigned, triggering Windows SmartScreen warnings. | Sign executable with an institutional Authenticode certificate or deploy via Active Directory GPO trust. |
| **SEC-04** | **MEDIUM** | `settings.py` | Default `DJANGO_SECRET_KEY` fallback is present in settings. | Enforce startup failure if `DJANGO_SECRET_KEY` is not provided via environment in production. |
| **SEC-05** | **LOW** | `accounts/views.py` | Login endpoint throttled at 20/min per IP, which may throttle multiple students behind a single NAT lab gateway. | Use Redis-backed user/IP combo throttling or configure Nginx `limit_req_zone` with appropriate burst buffers. |
