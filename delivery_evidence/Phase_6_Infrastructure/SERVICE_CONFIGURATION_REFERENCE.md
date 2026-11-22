# Phase 6: Service Configuration Reference

**Document:** Complete Environment Variable & Service Parameter Reference  

---

## 1. Django Backend Environment Variables

| Variable | Description | Default | Production Recommended |
|---|---|---|---|
| `DJANGO_DEBUG` | Django debug mode | `true` | `false` |
| `DJANGO_SECRET_KEY` | Cryptographic session & signing key | dev fallback | 64-char random hex string |
| `DJANGO_ALLOWED_HOSTS` | Permitted Host headers | `localhost,127.0.0.1` | `labora.college.edu,localhost` |
| `POSTGRES_DB` | Database name | empty (uses SQLite) | `labora` |
| `POSTGRES_USER` | Database username | `labora` | `labora_admin` |
| `POSTGRES_PASSWORD` | Database password | empty | Strong generated password |
| `POSTGRES_HOST` | Database hostname | `localhost` | `db` (container service name) |
| `POSTGRES_PORT` | Database port | `5432` | `5432` |
| `CELERY_BROKER_URL` | Redis message broker URL | None | `redis://:password@redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Redis task result backend | None | `redis://:password@redis:6379/1` |
| `CODE_EXECUTOR` | Code execution mode (`local`/`judge0`) | `judge0` | `judge0` (MANDATORY) |
| `JUDGE0_URL` | Judge0 server endpoint | `http://localhost:2358` | `http://judge0-server:2358` |
| `LABORA_SECURE_BROWSER_KEY` | Shared HMAC signing secret | dev fallback | 64-char random hex string |
| `TIME_ZONE` | Server timezone | `Asia/Kolkata` | `Asia/Kolkata` |

---

## 2. Judge0 Sandbox Configuration (`judge0.conf`)

| Parameter | Recommended Setting | Purpose |
|---|---|---|
| `CPU_TIME_LIMIT` | `5.0` | Maximum CPU seconds allowed per execution |
| `WALL_TIME_LIMIT` | `10.0` | Maximum total elapsed time allowed per run |
| `MEMORY_LIMIT` | `256000` | Maximum memory (256 MB) to prevent RAM exhaustion |
| `MAX_PROCESSES_AND_OR_THREADS` | `60` | Prevents fork bombs |
| `MAX_FILE_SIZE` | `2048` | Maximum file output size (2 KB) |
| `OUTPUT_LIMIT` | `64000` | Truncates stdout to 64 KB to protect network bandwidth |
