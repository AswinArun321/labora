# Phase 0: Baseline Architecture Analysis

**Document:** Baseline Architecture Verification  
**Source Baseline:** `LABORA-Test-Windows` as inventoried  

---

## 1. Architectural Topology Overview

The baseline system as shipped in the test kit is configured as a standalone, single-node evaluation kit:

```mermaid
flowchart TD
    subgraph Client["Client Tier"]
        EL["Electron Secure Browser (v1.0.0)\n- Runs Kiosk / dev mode\n- Intercepts requests & attaches HMAC\n- Scans processes every 30s\n- Flushes clipboard on blur/exit"]
        WB["Standard Web Browser (Chrome/Edge)\n- Unsigned requests (restricted practicals blocked)"]
    end

    subgraph Server["Single-Node Test Server (Django 5.x)"]
        WSGI["Django Runserver (Port 8000)\n- Single-threaded development server"]
        
        subgraph Apps["Django Core Apps"]
            ACC["accounts app\n- Custom User (Admin, Teacher, Student)\n- Subject, Department, CollegeSettings"]
            LABS["labs app\n- Practical, Submission, CodeVersion\n- ActivityEvent telemetry\n- Execution records"]
        end
        
        HMAC["labs.secure_browser\n- Verifies X-Labora-Signature against secret key\n- Enforces 300s timestamp skew"]
        EXEC["labs.executor\n- Synchronous execution dispatch\n- local subprocesses OR Judge0 API"]
        REC["labs.records\n- python-docx & WeasyPrint PDF"]
    end

    subgraph Storage["Storage Tier"]
        SQLITE["SQLite Database (db.sqlite3)\n- File-based database"]
        MEDIA["Local media / files"]
    end

    EL -->|"Signed API Calls"| WSGI
    WB -->|"Unsigned API Calls"| WSGI
    WSGI --> ACC
    WSGI --> LABS
    LABS --> HMAC
    LABS --> EXEC
    LABS --> REC
    ACC --> SQLITE
    LABS --> SQLITE
```

---

## 2. Key Architectural Invariants Discovered in Source

1. **Authentication:** Uses JWT authentication (`djangorestframework-simplejwt`). Tokens have 60-minute access and 12-hour refresh. Login endpoint is throttled (`20/min`).
2. **Kiosk Security Protocol:** Practicals with `require_secure_browser=True` verify that requests arrive with an HMAC signature computed from the current Unix timestamp, HTTP method, and full request path. Unsigned or expired requests receive an HTTP 403 Forbidden with `{"code": "secure_browser_required"}`.
3. **Execution Path:** The baseline contains two execution drivers in `labs/executor.py`:
   - `run_local`: Directly invokes `python -I`, `gcc`, or `javac/java` in temporary directories with subprocess timeouts.
   - `run_judge0`: Sends base64-encoded code to Judge0 via REST API. In the baseline code, this call uses `wait=true` (synchronous).
4. **Authoritative Record Integrity:** The lab record generation module (`labs/records.py`) strictly pulls the program output from an accepted `Execution` object linked to the submission (`record_execution`). Students cannot manually supply or edit the execution output that appears in their final record.
