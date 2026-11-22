# Phase 2: Production Kit Integration Gap Analysis

**Document:** Integration Gap List  
**Target:** Staging Deployment Readiness  

---

## 1. Verified Integration Points

| Component | Target Location in Project | Integration Status | Notes |
|---|---|---|---|
| Celery App | `server/backend/labora/celery.py` | Ready to merge | Exposes standard Celery application |
| Tasks | `server/backend/labs/tasks.py` | Ready to merge | Celery autodiscovery finds `labs.tasks` |
| Async Views | `server/backend/labs/views.py` | Ready to merge | Can be appended without breaking existing endpoints |
| Async URLs | `server/backend/labora/urls.py` | Ready to merge | Route: `path("workspace/<int:practical_id>/run-async/", ...)` |
| Execution Model | `server/backend/labs/models.py` | Requires Migration | Add `judge0_token` and `status` choices |
| Docker Compose | Root or `deploy/` | Self-contained | Operates out of `production_kit/docker/` |

---

## 2. Gaps & Action Items for College Deployment

1. **Database Migration Generation:**
   - *Action:* Run `python manage.py makemigrations labs` on a staging copy after adding fields from `models_extension.py` to `labs/models.py`.
   - *Rollback:* Standard Django migration rollback (`python manage.py migrate labs 0001`).

2. **Environment Secrets Generation:**
   - *Action:* Generate cryptographically secure keys (via `openssl rand -hex 32`) for `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and `LABORA_SECURE_BROWSER_KEY` in `production_kit/docker/.env`.
   - *Security Check:* Ensure `.env` is never committed to public version control.

3. **Frontend API Endpoint Alignment:**
   - *Action:* When toggling the frontend from synchronous `/run/` to asynchronous `/run-async/`, ensure the React SPA handles polling on `/executions/<id>/` until `is_complete: true`.
   - *Fallback:* Existing synchronous `/run/` endpoint remains fully functional in the backend for backward compatibility.
