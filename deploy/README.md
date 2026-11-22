# LABORA Production Deployment Kit

This directory provides the production-grade, self-hosted deployment artifacts for **LABORA — Secure Programming Practical Examination and Digital Lab Record Management System**.

## Stack Components

| Service | Technology | Port / Network | Purpose |
|---------|-----------|----------------|---------|
| `nginx` | Nginx Alpine | `80:80`, `443:443` (Public) | Reverse proxy, SSL/TLS, static asset caching, rate limiting |
| `backend` | Django 5 + Gunicorn | `8000` (Internal) | REST API, authentication, submission handling |
| `celery_worker` | Celery 5.3 + Python | Internal | Non-blocking execution dispatcher & polling |
| `celery_beat` | Celery Beat | Internal | Scheduled tasks & stale execution reconciler |
| `redis` | Redis 7 Alpine | `6379` (Internal) | Task broker (db 0), result backend (db 1), shared cache (db 2) |
| `db` | PostgreSQL 16 Alpine | `5432` (Internal) | Relational database with persistent storage |
| `judge0-server` | Judge0 1.13.1 | `2358` (Internal) | Sandboxed compiler & runtime runner |
| `judge0-db` | PostgreSQL 13 Alpine | Internal | Judge0 isolated submission database |
| `judge0-redis` | Redis 7 Alpine | Internal | Judge0 isolated execution queue |

## Quick Start Deployment

1. **Clone repository & enter deploy directory:**
   ```bash
   cd deploy
   ```

2. **Configure production environment:**
   ```bash
   cp .env.production.example .env
   # Edit .env and replace all secret keys, passwords, and DOMAIN_NAME
   nano .env
   ```

3. **Build and start services:**
   ```bash
   docker compose up -d --build
   ```

4. **Verify stack health:**
   ```bash
   bash health_check.sh
   # Or query the API health endpoint
   curl -k https://localhost/api/health/
   ```

5. **Create administrative superuser:**
   ```bash
   docker exec -it labora-backend python manage.py createsuperuser
   ```

## Backup & Recovery

- **Automated Backup:**
  ```bash
  bash backup.sh
  ```
- **Restore from Backup:**
  ```bash
  bash restore.sh /path/to/labora_backup_YYYYMMDD_HHMMSS.sql.gz
  ```
