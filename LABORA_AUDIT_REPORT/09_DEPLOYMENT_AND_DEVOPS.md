# LABORA — Production Deployment & DevOps Audit

**Deployment Specification:** `production_kit/docker/docker-compose.prod.yml`, `production_kit/docker/Dockerfile.backend`, `production_kit/nginx/nginx.conf`  
**Target Host OS:** Linux (Ubuntu Server 22.04 LTS Recommended)  
**Budget Objective:** ₹0 Software License / Cloud Cost (Self-hosted on College Hardware)  

---

## 1. Production Container Orchestration Topology

```mermaid
flowchart TD
    Client["Client (Browser / Secure Browser)"]
    
    subgraph Host["College Host Server (Docker Compose)"]
        subgraph Edge["Public Ingress (Bridge: 80, 443)"]
            Nginx["labora-nginx (nginx:alpine)\n- Port 80 -> 301 Redirect\n- Port 443 -> SSL Termination\n- Rate Limiting (IP & Student Client ID)\n- Static SPA & Media Caching"]
        end

        subgraph InternalNet["Network: labora-internal (Bridge)"]
            Backend["labora-backend (python:3.11-slim)\n- Gunicorn WSGI (4 Workers)\n- Django 5.2 API Layer"]
            Celery["labora-celery-worker (python:3.11-slim)\n- Celery 5.3 Worker\n- Concurrency = 8"]
            Postgres["labora-db (postgres:16-alpine)\n- Authoritative Database\n- Volume: postgres_data"]
            Redis["labora-redis (redis:7-alpine)\n- Append-Only Persistence (AOF)\n- Task Broker (db 0) & Cache (db 1)"]
            Judge0Server["labora-judge0-server (judge0/judge0:1.13.1)\n- Port 2358\n- Sandbox Execution Dispatcher"]
        end

        subgraph Judge0Net["Network: judge0-net (Internal Bridge)"]
            Judge0Db["labora-judge0-db (postgres:13-alpine)\n- Volume: judge0_db_data"]
            Judge0Redis["labora-judge0-redis (redis:7-alpine)"]
        end
    end

    Client -->|HTTPS (443)| Nginx
    Nginx -->|Reverse Proxy :8000| Backend
    Backend --> Postgres
    Backend --> Redis
    Backend -->|Enqueue| Celery
    Celery --> Redis
    Celery --> Postgres
    Celery -->|POST /submissions| Judge0Server
    Judge0Server --> Judge0Db
    Judge0Server --> Judge0Redis
```

---

## 2. Service Inventory & Configuration

From `production_kit/docker/docker-compose.prod.yml`:

| Service Name | Base Container Image | Exposed Ports | Volumes / Mounts | Restart Policy | Health Check |
|---|---|---|---|---|---|
| `db` | `postgres:16-alpine` | None (Internal) | `postgres_data:/var/lib/postgresql/data`, `./backups/db:/backups` | `always` | `pg_isready -U labora_admin -d labora` (10s interval) |
| `redis` | `redis:7-alpine` | None (Internal) | `redis_data:/data` | `always` | `redis-cli -a <password> ping` (10s interval) |
| `backend` | Built from `Dockerfile.backend` | None (Internal) | `media_data:/app/media`, `static_data:/app/staticfiles` | `always` | **None defined** |
| `celery_worker`| Built from `Dockerfile.backend` | None (Internal) | None | `always` | **None defined** |
| `judge0-server`| `judge0/judge0:1.13.1` | None (Internal) | `./judge0.conf:/judge0.conf:ro` | `always` | **None defined** |
| `judge0-db` | `postgres:13-alpine` | None (Internal) | `judge0_db_data:/var/lib/postgresql/data` | `always` | **None defined** |
| `judge0-redis`| `redis:7-alpine` | None (Internal) | None | `always` | **None defined** |
| `nginx` | `nginx:alpine` | `80:80`, `443:443` | `nginx.conf:/etc/nginx/conf.d/default.conf:ro`, `server/frontend/dist:/var/www/labora:ro`, `/etc/letsencrypt:/etc/letsencrypt:ro` | `always` | **None defined** |

---

## 3. Can the Current Production Configuration Actually Start?

> [!WARNING]
> **Static Inspection Assessment:** If `docker compose -f docker-compose.prod.yml up -d` is executed on a clean staging server without prior manual intervention, **THE STACK WILL FAIL TO START**.
>
> The following four concrete blockers prevent out-of-the-box startup:

### Blocker 1: Nginx Fails to Start due to Missing SSL Certificates
- In `production_kit/nginx/nginx.conf`:
  ```nginx
  server {
      listen 443 ssl http2;
      ssl_certificate /etc/letsencrypt/live/labora/fullchain.pem;
      ssl_certificate_key /etc/letsencrypt/live/labora/privkey.pem;
      ...
  ```
- In `docker-compose.prod.yml`:
  `volumes: - /etc/letsencrypt:/etc/letsencrypt:ro`
- **The Failure:** On a newly provisioned server, `/etc/letsencrypt/live/labora/` does not exist. Nginx tests configuration syntax on container boot, encounters `BIO_new_file() failed (No such file or directory)`, and crashes in a continuous restart loop (`Restarting (1) 2 seconds ago`).
- **Remediation:** Provide an initial HTTP-only bootstrap configuration or a self-signed certificate generation script to allow initial ACME challenge / certbot issuance.

### Blocker 2: Judge0 Container Missing Linux `cgroups` & `privileged` Flags
- In `docker-compose.prod.yml`, `judge0-server` is configured as a standard non-privileged container:
  ```yaml
  judge0-server:
    image: judge0/judge0:1.13.1
    container_name: labora-judge0-server
    restart: always
  ```
- **The Failure:** Judge0 CE executes untrusted code using `isolate`, which requires Linux kernel `cgroups` v1/v2 controller access and specific kernel privileges. Without `privileged: true` and mounting `/sys/fs/cgroup:/sys/fs/cgroup:ro`, Judge0 CE fails to initialize worker sandboxes, returning `500 Internal Server Error` on every code submission.
- **Remediation:** Update `judge0-server` in `docker-compose.prod.yml`:
  ```yaml
  privileged: true
  volumes:
    - ./judge0.conf:/judge0.conf:ro
    - /sys/fs/cgroup:/sys/fs/cgroup:ro
  ```

### Blocker 3: Django Backend Starts Against Empty Database Without Migrations
- In `Dockerfile.backend`, the entry point is:
  ```dockerfile
  CMD ["gunicorn", "labora.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", ...]
  ```
- **The Failure:** When PostgreSQL first initializes, the database is completely empty. `labora-backend` starts immediately and Gunicorn begins serving requests before `manage.py migrate` is executed. Any incoming API call returns `relation "accounts_collegesettings" does not exist` (HTTP 500).
- **Remediation:** Add an entrypoint script `docker-entrypoint.sh` that waits for PostgreSQL readiness using `pg_isready`, runs `python manage.py migrate --noinput`, runs `python manage.py collectstatic --noinput`, and then invokes Gunicorn.

### Blocker 4: Missing Static Assets Collection
- In `docker-compose.prod.yml`, Nginx mounts `static_data:/var/www/static:ro` and Django mounts `static_data:/app/staticfiles`.
- **The Failure:** Django admin stylesheets and DRF browsable API CSS/JS are never copied to `staticfiles` because `python manage.py collectstatic` is not run during container build or startup. As a result, accessing `/django-admin/` serves unstyled HTML.
- **Remediation:** Automate `collectstatic` in the entrypoint script.

---

## 4. Disaster Recovery & Maintenance Scripts Audit

Located in `production_kit/scripts/`:

### 4.1 Database Backup Script (`backup_postgres.sh`)
- **Status:** **Implemented & Syntactically Sound**
- **Features:**
  - Invokes `docker exec labora-db pg_dump -U labora_admin labora | gzip -9 > backup.sql.gz`.
  - Generates SHA256 checksum: `sha256sum backup.sql.gz > backup.sql.gz.sha256`.
  - Checks if file size is > 1024 bytes to catch empty dumps.
  - Automatic rotation: Deletes backups older than 30 days (`find -mtime +30 -delete`).

### 4.2 Database Restore Script (`restore_postgres.sh`)
- **Status:** **Implemented & Syntactically Sound**
- **Features:**
  - Requires explicit confirmation: `Type 'RESTORE' to confirm`.
  - Verifies SHA256 checksum before execution if `.sha256` file exists.
  - Terminates active connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity...`.
  - Drops and recreates the target database.
  - Streams decompressed SQL into `docker exec -i labora-db psql`.

### 4.3 Diagnostic Health Audit Script (`health_check.sh`)
- **Status:** **Implemented & Syntactically Sound**
- **Features:**
  - Audits container statuses via `docker ps`.
  - Tests PostgreSQL readiness via `pg_isready`.
  - Checks Celery queue backlog via Redis `llen celery`.
  - Queries Judge0 system status: `GET http://judge0-server:2358/system_info`.
  - Reports Docker volume storage utilization via `df -h /var/lib/docker`.
