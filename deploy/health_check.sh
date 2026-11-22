#!/bin/bash
# ==============================================================================
# LABORA Production Infrastructure Diagnostic & Health Audit
# Validates container statuses, Redis queue depths, and Judge0 connectivity
# ==============================================================================

echo "=== LABORA HEALTH AUDIT ==="
date

echo -e "\n[1. Container Statuses]"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo -e "\n[2. Database Connection Check]"
docker exec labora-db pg_isready -U "${POSTGRES_USER:-labora_admin}" -d "${POSTGRES_DB:-labora}" && echo "PostgreSQL: HEALTHY" || echo "PostgreSQL: FAILED"

echo -e "\n[3. Redis & Celery Queue Backlog]"
QUEUED_JOBS=$(docker exec labora-redis redis-cli -a "${REDIS_PASSWORD:-RedisSecurePass456}" --no-auth-warning llen celery 2>/dev/null || echo "0")
echo "Pending Celery tasks in queue: ${QUEUED_JOBS}"

echo -e "\n[4. Application API Health Endpoint]"
APP_HEALTH=$(docker exec labora-backend curl -s http://localhost:8000/api/health/ 2>/dev/null || echo "FAILED")
echo "Django Backend API Health: ${APP_HEALTH}"

echo -e "\n[5. Judge0 Execution Runner Check]"
JUDGE0_STATUS=$(docker exec labora-backend curl -s -o /dev/null -w "%{http_code}" http://judge0-server:2358/system_info 2>/dev/null || echo "FAILED")
if [ "${JUDGE0_STATUS}" == "200" ]; then
    echo "Judge0 API: REACHABLE (HTTP 200)"
else
    echo "Judge0 API: UNREACHABLE (HTTP ${JUDGE0_STATUS})"
fi

echo -e "\n=== AUDIT COMPLETE ==="
