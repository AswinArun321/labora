# LABORA Production Operational Runbooks

**Reference:** `plann.md` Section 20  
**Scope:** Standard Operating Procedures (SOP) for College System Administrators  
**Deployment Environment:** Ubuntu Server LTS with Docker Compose  

---

## SOP-01: Service Lifecycle Management (Start / Stop / Restart)

### 1.1 Starting All Services
```bash
cd /opt/labora/production_kit/docker
docker compose -f docker-compose.prod.yml up -d
```
Verify startup health:
```bash
docker compose -f docker-compose.prod.yml ps
```

### 1.2 Stopping Services Gracefully
```bash
# Stop celery worker first so in-flight tasks finish
docker compose -f docker-compose.prod.yml stop celery_worker
# Stop application and web proxy
docker compose -f docker-compose.prod.yml stop nginx backend
# Stop database and redis queues
docker compose -f docker-compose.prod.yml stop redis db judge0-server judge0-db judge0-redis
```

### 1.3 Restarting an Individual Service (e.g. Backend)
```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## SOP-02: Deploying a New Application Release

1. **Pull or archive new release assets:**
   ```bash
   cd /opt/labora
   git pull origin main # or extract new release bundle
   ```
2. **Rebuild the backend image without downtime:**
   ```bash
   cd production_kit/docker
   docker compose -f docker-compose.prod.yml build backend
   ```
3. **Run database migrations:**
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate
   ```
4. **Collect static assets:**
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput
   ```
5. **Restart backend and celery containers:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker
   ```

---

## SOP-03: Applying Database Migrations Safely

Before applying migrations in production:
1. **Take an instant snapshot backup:**
   ```bash
   bash /opt/labora/production_kit/scripts/backup_postgres.sh
   ```
2. **Execute migration plan in dry-run mode:**
   ```bash
   docker exec -it labora-backend python manage.py showmigrations
   ```
3. **Apply migrations:**
   ```bash
   docker exec -it labora-backend python manage.py migrate
   ```

---

## SOP-04: Secrets & Credentials Rotation

When rotating `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, or `LABORA_SECURE_BROWSER_KEY`:

1. Update the `.env` file in `/opt/labora/production_kit/docker/.env`.
2. For database password rotation, update PostgreSQL internal credentials first:
   ```bash
   docker exec -it labora-db psql -U labora_admin -d labora -c "ALTER USER labora_admin WITH PASSWORD 'NewPassword789';"
   ```
3. Re-launch backend and workers with the new environment:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
4. If rotating `LABORA_SECURE_BROWSER_KEY`:
   - Update `labora.config.json` on client lab machines.
   - Practicals requiring the secure browser will reject old clients once the backend key is changed.

---

## SOP-05: Scaling & Managing Judge0 Runners

### 5.1 Adding an Additional Judge0 Worker
If queue delays exceed 5 seconds under heavy bursts:
1. Deploy an additional Judge0 runner host (e.g. `192.168.1.50:2358`).
2. Add runner endpoint into Django settings `JUDGE0_POOL = ["http://judge0-server:2358", "http://192.168.1.50:2358"]`.
3. Restart Celery dispatcher:
   ```bash
   docker compose -f docker-compose.prod.yml restart celery_worker
   ```

### 5.2 Removing / Draining a Runner for Maintenance
1. Remove the target runner from the active pool list in settings.
2. Allow active submissions to complete (tokens are checked against the specific originating runner).

---

## SOP-06: Checking & Draining Execution Queues

### 6.1 Inspect Queue Depth
```bash
docker exec -it labora-redis redis-cli -a "$REDIS_PASSWORD" llen celery
```

### 6.2 Purging Stuck or Flooded Queue (Emergency Only)
```bash
docker exec -it labora-redis redis-cli -a "$REDIS_PASSWORD" del celery
```

---

## SOP-07: Backup & Disaster Recovery Procedures

### 7.1 Automated Daily Backup Schedule (Cron)
Add to `/etc/crontab`:
```cron
0 2 * * * root /bin/bash /opt/labora/production_kit/scripts/backup_postgres.sh >> /var/log/labora_backup.log 2>&1
```

### 7.2 Manual Database Restoration
```bash
bash /opt/labora/production_kit/scripts/restore_postgres.sh /var/backups/labora/labora_backup_YYYYMMDD_HHMMSS.sql.gz
```

---

## SOP-08: Handling Failed or Stuck Executions

If a student's execution remains stuck in `PROCESSING`:
1. Check Celery worker logs:
   ```bash
   docker logs --tail 100 labora-celery-worker
   ```
2. Check Judge0 container logs:
   ```bash
   docker logs --tail 100 labora-judge0-server
   ```
3. Reset stuck execution records older than 5 minutes:
   ```bash
   docker exec -it labora-backend python manage.py shell -c "
   from labs.models import Execution; from django.utils import timezone; from datetime import timedelta;
   stuck = Execution.objects.filter(status__in=['QUEUED','PROCESSING'], created_at__lt=timezone.now()-timedelta(minutes=5));
   print(f'Resetting {stuck.count()} stuck executions');
   stuck.update(status='FAILED', stderr='Execution timed out on worker.')
   "
   ```

---

## SOP-09: Interrupted Examination Recovery

If power, network, or server crashes during an active exam:
1. **Bring services back online:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
2. **Verify Student Data Integrity:**
   - All student code autosaved prior to the crash is preserved in PostgreSQL (`labs_submission` and `labs_codeversion`).
   - When students log back in from the Secure Browser, their latest code automatically loads.
3. **If Exam Window Expired:**
   - Teacher or Admin extends `due_date` on the practical via `/api/practicals/<id>/`.

---

## SOP-10: Client Secure Browser Deployment & Updates

1. **Deploying to College Lab PCs:**
   - Copy `Secure Browser/` directory to `C:\Program Files\LABORA\` on client computers.
   - Distribute via Active Directory Group Policy (GPO) or network share.
2. **Configuring Endpoint:**
   - Set `serverUrl` in `labora.config.json` to the college server domain (e.g., `https://labora.college.edu`).
3. **Handling Windows SmartScreen:**
   - Run once as admin or add an exclusion for `LABORA Secure Browser.exe` in Windows Defender.

---

## SOP-11: Reviewing Security Alerts & Audit Trails

1. Log in to the Teacher / Admin portal.
2. Navigate to **Practical -> Submissions -> Review Indicators**.
3. Indicators flagged by the system:
   - `large_insertion`: Suspicious block of pasted code (120+ chars).
   - `blocked_paste`: External copy/paste attempt blocked by the browser.
   - `left_window`: Student minimized or navigated away from the exam screen.
   - `secure_alert`: Blacklisted process detected (ChatGPT, WhatsApp, VS Code).
   - `normal_browser`: Practical opened without valid HMAC signature.

---

## SOP-12: Resource Saturation Response

### 12.1 High CPU / Load Average
- Check top resource consumers: `docker stats`
- Scale Celery workers down temporarily if compiler compilation saturates host cores:
  ```bash
  docker exec -it labora-celery-worker celery -A labora control autoscale 4 2
  ```

### 12.2 Disk Capacity Alerts
- Prune Docker build caches and dead volumes:
  ```bash
  docker system prune -af --volumes
  ```
- Clear old Judge0 sandbox temp directories in `/tmp`.
