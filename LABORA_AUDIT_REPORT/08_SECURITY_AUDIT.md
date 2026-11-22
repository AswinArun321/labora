# LABORA — Comprehensive Application Security Audit & Threat Model

**Audit Type:** Static Application Security Testing (SAST) & Threat Modeling  
**Compliance Standards:** OWASP Top 10 (2021), ASVS Level 2, Collegiate Security Standards  
**Scope:** Complete repository (Backend, Electron Client, Docker/Nginx, Scripts)  

---

## 1. Executive Vulnerability Classification Matrix

| Vulnerability ID | Vulnerability Title | Severity | Affected Component / File | OWASP 2021 Category | Remediation Urgency |
|---|---|---|---|---|---|
| **SEC-01** | Arbitrary Remote Code Execution (RCE) via Local Runner | **CRITICAL** | `server/backend/labs/executor.py` (`run_local`) | A03: Injection | Immediate |
| **SEC-02** | Hardcoded Insecure Fallback `DJANGO_SECRET_KEY` | **CRITICAL** | `server/backend/labora/settings.py` | A02: Cryptographic Failures | Immediate |
| **SEC-03** | Cleartext Shared HMAC Secret in Electron Client | **HIGH** | `Secure Browser/labora.config.json` | A07: Identification & Auth | High |
| **SEC-04** | Client Kiosk Security Bypass via `--dev` Flag | **HIGH** | `Secure Browser/resources/app/main.js` | A07: Identification & Auth | High |
| **SEC-05** | Sensitive Sandbox Token Exposure via REST API | **HIGH** | `server/backend/labs/serializers.py` | A01: Broken Access Control | High |
| **SEC-06** | Hardcoded Database Passwords in Production Compose | **HIGH** | `production_kit/docker/docker-compose.prod.yml` | A05: Security Misconfig | High |
| **SEC-07** | Stale Execution Verification Flaw in Submission | **MEDIUM** | `server/backend/labs/views.py` (`workspace_submit`) | A04: Insecure Design | Medium |
| **SEC-08** | Missing Atomic Transactions & Concurrency Locks | **MEDIUM** | `server/backend/labs/views.py` | A04: Insecure Design | Medium |
| **SEC-09** | Weak Minimum Password Policy (6 Characters) | **MEDIUM** | `server/backend/labora/settings.py` | A07: Identification & Auth | Medium |
| **SEC-10** | Default Username-as-Password in CSV Student Import | **LOW** | `server/backend/accounts/views.py` (`import_csv`) | A07: Identification & Auth | Low |
| **SEC-11** | Missing Content Security Policy (CSP) Headers | **LOW** | `server/backend/labora/settings.py` / `nginx.conf` | A05: Security Misconfig | Low |
| **SEC-12** | Permissive Default CORS Origins | **INFO** | `server/backend/labora/settings.py` | A05: Security Misconfig | Pre-Deployment |

---

## 2. In-Depth Technical Vulnerability Reports

### SEC-01: Arbitrary Remote Code Execution (RCE) via Local Runner
- **Severity:** **CRITICAL (CVSS 9.8)**
- **Affected File:** [server/backend/labs/executor.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/executor.py#L82-L127) (`run_local`), [labora/settings.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/settings.py#L123)
- **Technical Explanation:** When `CODE_EXECUTOR="local"`, student source code is compiled and executed directly on the host operating system using `subprocess.run([sys.executable, "-I", path])`, `gcc`, or `javac`. The subprocess inherits the operating system privileges of the Django server process without containerization, cgroup sandboxing, or user namespace isolation.
- **Root Cause Defect:** In `labora/settings.py`, there is **no sanity check** restricting `CODE_EXECUTOR="local"` to development. If an administrator accidentally leaves `CODE_EXECUTOR=local` in the production `.env` or Docker configuration while `DJANGO_DEBUG=False`, untrusted student code executes directly on the server.
- **Potential Impact:** Complete host server compromise. A student can execute `__import__('os').system('rm -rf /')`, extract database credentials, steal exam questions, or deploy ransomware.
- **Recommended Fix:** Add a strict startup validation guard in `labora/settings.py`:
  ```python
  if not DEBUG and CODE_EXECUTOR == "local":
      raise ImproperlyConfigured("CODE_EXECUTOR='local' is strictly prohibited in production (DEBUG=False). Use 'judge0'.")
  ```

---

### SEC-02: Hardcoded Insecure Fallback `DJANGO_SECRET_KEY`
- **Severity:** **CRITICAL (CVSS 9.1)**
- **Affected File:** [server/backend/labora/settings.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/settings.py#L32)
- **Technical Explanation:** The setting uses:
  ```python
  SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-in-production-0000")
  ```
- **Potential Impact:** If the environment variable `DJANGO_SECRET_KEY` is omitted or empty during deployment, Django silently falls back to this publicly known string. An attacker who knows this key can forge Django session cookies, bypass CSRF verification, and tamper with cryptographic tokens.
- **Recommended Fix:** Require the secret key to be set when `DEBUG=False`:
  ```python
  SECRET_KEY = env("DJANGO_SECRET_KEY")
  if not SECRET_KEY:
      if DEBUG:
          SECRET_KEY = "dev-only-insecure-key-change-me-in-production-0000"
      else:
          raise ImproperlyConfigured("DJANGO_SECRET_KEY environment variable is mandatory in production.")
  ```

---

### SEC-03: Cleartext Shared HMAC Secret in Electron Client
- **Severity:** **HIGH (CVSS 7.5)**
- **Affected File:** [Secure Browser/labora.config.json](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/labora.config.json#L3), [labs/secure_browser.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/secure_browser.py#L31)
- **Technical Explanation:** The HMAC-SHA256 client attestation relies on symmetric cryptography where both the backend and every client hold the identical pre-shared key (`"browserKey": "change-this-shared-browser-key"`). In `labora.config.json`, this key is stored unencrypted in plain JSON on student computers.
- **Potential Impact:** Any student can inspect `labora.config.json`, extract the secret key, and forge valid `X-Labora-Ts` and `X-Labora-Signature` headers using Python or a standard browser extension, completely defeating the Secure Browser restriction.
- **Recommended Fix:**
  1. Restrict filesystem permissions on lab computers so student accounts cannot read the installation folder (`icacls "C:\Program Files\LABORA" /deny Students:(F)`).
  2. Transition to asymmetric client attestation (e.g., embedding a client private key inside a protected Windows DPAPI store or verifying machine certificate via mutual TLS).

---

### SEC-04: Client Kiosk Security Bypass via `--dev` Flag
- **Severity:** **HIGH (CVSS 7.2)**
- **Affected File:** [Secure Browser/resources/app/main.js](file:///d:/v/LABORA-Test-Windows/Secure%20Browser/resources/app/main.js#L20)
- **Technical Explanation:** `main.js` contains the logic:
  ```javascript
  const DEV = process.argv.includes('--dev') || process.env.LABORA_DEV === '1'
  ```
  When launched with `--dev`, the browser sets `kiosk: false`, `fullscreen: false`, `alwaysOnTop: false`, and enables `devTools: true`.
- **Potential Impact:** A student can launch the executable with `--dev` from the command line or via `3 - SECURE BROWSER (windowed test mode).bat`, opening DevTools to inspect code, paste AI solutions, or browse external websites in split-screen.
- **Recommended Fix:** In production builds, conditionally strip `--dev` flag parsing completely:
  ```javascript
  const DEV = !app.isPackaged && (process.argv.includes('--dev') || process.env.LABORA_DEV === '1')
  ```

---

### SEC-05: Sensitive Sandbox Token Exposure via REST API
- **Severity:** **HIGH (CVSS 6.5)**
- **Affected File:** [server/backend/labs/serializers.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/serializers.py#L31)
- **Technical Explanation:** `ExecutionSerializer` exposes the field `judge0_token` in its serialized output. When a student polls `GET /api/executions/<id>/`, the response contains the internal UUID token generated by Judge0.
- **Potential Impact:** If the internal Judge0 container port (`2358`) is exposed or accessible on the college subnet, students can query Judge0 directly, inspect other submissions, or inject commands.
- **Recommended Fix:** Remove `judge0_token` from `ExecutionSerializer.Meta.fields`. The token is an internal implementation detail and must never be exposed to clients.

---

### SEC-06: Hardcoded Default Passwords in Production Docker Compose
- **Severity:** **HIGH (CVSS 7.4)**
- **Affected File:** [production_kit/docker/docker-compose.prod.yml](file:///d:/v/LABORA-Test-Windows/production_kit/docker/docker-compose.prod.yml)
- **Technical Explanation:** The YAML file defines default fallback credentials directly in plaintext:
  - `POSTGRES_PASSWORD:-ChangeMeSecurePassword123`
  - `REDIS_PASSWORD:-RedisSecurePass456`
  - `Judge0DbPassSecret789`
- **Potential Impact:** If deployed without configuring a `.env` file, the production PostgreSQL database and Redis queue use publicly known passwords.
- **Recommended Fix:** Remove default fallback passwords from `docker-compose.prod.yml`. Require all passwords to be supplied via an external, Git-ignored `.env` file (`${POSTGRES_PASSWORD:?Database password is required}`).

---

### SEC-07: Stale Execution Verification Flaw in Submission
- **Severity:** **MEDIUM (CVSS 5.3)**
- **Affected File:** [server/backend/labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py#L312-L318)
- **Technical Explanation:** In `workspace_submit`:
  ```python
  last_ok = sub.executions.filter(status="Accepted", state=Execution.State.COMPLETED).order_by("-created_at").first()
  if not last_ok or last_ok.code != code:
      return Response({"detail": "Run your final program successfully...", "code": "run_required"}, status=400)
  ```
  This query looks for the *most recent accepted execution*. If a student ran code `A` successfully earlier, then modified code to `B` (which failed with a syntax or runtime error), and subsequently restored code to `A`, `last_ok` successfully retrieves the older execution. The student can submit code `A` without running it in the current session. Furthermore, if a newer execution of `A` is currently in flight (`PROCESSING`) with different stdin, the stale accepted execution is attached to `sub.record_execution`.
- **Recommended Fix:** Ensure that the *most recent execution overall* (`sub.executions.order_by("-created_at").first()`) has `status="Accepted"` and `state="COMPLETED"`:
  ```python
  latest = sub.executions.order_by("-created_at").first()
  if not latest or latest.code != code or latest.status != "Accepted" or latest.state != Execution.State.COMPLETED:
      return Response({"detail": "You must run your latest program successfully before submitting.", "code": "run_required"}, status=400)
  ```

---

### SEC-08: Missing Atomic Transactions & Concurrency Locks
- **Severity:** **MEDIUM (CVSS 4.7)**
- **Affected File:** [server/backend/labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py#L309-L325) (`workspace_submit`), [labs/views.py](file:///d:/v/LABORA-Test-Windows/server/backend/labs/views.py#L350-L362) (`submission_approve`)
- **Technical Explanation:** Neither `workspace_submit` nor `submission_approve` wraps database modifications in `with transaction.atomic():` with `select_for_update()`.
- **Potential Impact:** Concurrent requests can trigger race conditions where a student submits twice, or where a teacher approves a submission while a correction request or save is processing in parallel.
- **Recommended Fix:** Wrap state transitions in `transaction.atomic()` with `Submission.objects.select_for_update()`.

---

### SEC-09: Weak Password Policy
- **Severity:** **MEDIUM (CVSS 4.3)**
- **Affected File:** [server/backend/labora/settings.py](file:///d:/v/LABORA-Test-Windows/server/backend/labora/settings.py#L88-L90)
- **Technical Explanation:** `AUTH_PASSWORD_VALIDATORS` contains only `MinimumLengthValidator(min_length=6)`. Common password, numeric, and attribute similarity validators are disabled.
- **Recommended Fix:** Enable standard Django password validators in `settings.py`.
