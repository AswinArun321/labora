# LABORA — Production Deployment Guide

**Document:** `production_kit/docs/DEPLOYMENT_GUIDE.md`  
**Target:** Ubuntu Server 22.04 / 24.04 LTS with Docker Compose  
**Budget:** ₹0 Additional Software / API Expenditure  

---

## 1. Quick Production Deployment Steps

```bash
# 1. Update system and install Docker
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker

# 2. Clone or copy project to /opt/labora
sudo mkdir -p /opt/labora && sudo chown -R $USER:$USER /opt/labora
cd /opt/labora

# 3. Configure production secrets in production_kit/docker/.env
cd production_kit/docker
cat << 'EOF' > .env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_DB=labora
POSTGRES_USER=labora_admin
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
LABORA_SECURE_BROWSER_KEY=$(openssl rand -hex 32)
DOMAIN_NAME=labora.yourcollege.edu
EOF

# 4. Launch multi-container stack
docker compose -f docker-compose.prod.yml up -d

# 5. Run database migrations
docker exec -it labora-backend python manage.py migrate

# 6. Create administrator account
docker exec -it labora-backend python manage.py createsuperuser

# 7. Verify infrastructure health
bash ../scripts/health_check.sh
```

---

## 2. Production Service Architecture

| Service Name | Container Image | Port Binding | Purpose |
|---|---|---|---|
| `nginx` | `nginx:alpine` | `80:80`, `443:443` | Reverse proxy, SSL, rate limiting, static asset host |
| `backend` | Built from `Dockerfile.backend` | Internal `8000` | Django 5.x Gunicorn REST API |
| `celery_worker`| Built from `Dockerfile.backend` | Internal | Asynchronous execution dispatcher & polling worker |
| `db` | `postgres:16-alpine` | Internal `5432` | Persistent transactional relational database |
| `redis` | `redis:7-alpine` | Internal `6379` | Task queue broker & cache |
| `judge0-server`| `judge0/judge0:1.13.1` | Internal `2358` | Isolated code execution sandbox daemon |
| `judge0-db` | `postgres:13-alpine` | Internal | Judge0 isolated database |
| `judge0-redis` | `redis:7-alpine` | Internal | Judge0 isolated queue |
