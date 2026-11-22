# Phase 3: Reproducible Development Guide

**Document:** Developer Setup & Engineering Standards  
**Target:** Local Development, Linting, Testing, and Staging  

---

## 1. System Prerequisites

* **Operating System:** Windows 10/11, macOS, or Ubuntu 22.04/24.04 LTS
* **Python Runtime:** Python 3.10, 3.11, or 3.12 (with `python` and `pip` on PATH)
* **Compilers:**
  - Python: Built-in runtime
  - C: GCC (MSYS2/MinGW on Windows, `build-essential` on Linux)
  - Java: OpenJDK 17 or 21 (`javac` and `java` on PATH)
* **Node.js (Optional):** Node.js 18+ for building the Electron client or React SPA.

---

## 2. Setting Up Local Development

```bash
# 1. Navigate to backend directory
cd server/backend

# 2. Create isolated virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements-test.txt

# 5. Apply database migrations
python manage.py migrate

# 6. Seed demo accounts and MCA curriculum practicals
python manage.py seed_demo --secure-langs c

# 7. Start local development server
python manage.py runserver 127.0.0.1:8000
```

---

## 3. Running Automated Tests

```bash
# Cross-platform test execution
python manage.py test
```

---

## 4. Coding & Security Standards

1. **Environment Variables:** All secrets, keys, and hosts must be ingested via `os.environ.get()` with safe development fallbacks. Never hardcode passwords or cryptographic keys.
2. **Object-Level Permissions:** Always enforce subject and student tenancy checks on every view.
3. **Immutable Submissions:** Never allow modifications to a submission once its status is `submitted` or `approved`.
4. **Execution Isolation:** Untrusted student code must always run with CPU time and memory limits.
