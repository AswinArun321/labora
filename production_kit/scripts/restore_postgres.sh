#!/bin/bash
# ==============================================================================
# LABORA Production PostgreSQL Restoration Script
# Restores a verified backup file into the active database container
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 /path/to/labora_backup_YYYYMMDD_HHMMSS.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="labora-db"
DB_USER="${POSTGRES_USER:-labora_admin}"
DB_NAME="${POSTGRES_DB:-labora}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "[ERROR] File not found: ${BACKUP_FILE}"
    exit 1
fi

# Verify checksum if present
if [ -f "${BACKUP_FILE}.sha256" ]; then
    echo "[INFO] Verifying SHA256 checksum..."
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

echo "========================================================================"
echo " WARNING: THIS WILL OVERWRITE ALL EXISTING DATA IN DATABASE '${DB_NAME}'"
echo " Target Container: ${CONTAINER_NAME}"
echo " Backup File:      ${BACKUP_FILE}"
echo "========================================================================"
read -p "Type 'RESTORE' to confirm: " CONFIRM

if [ "${CONFIRM}" != "RESTORE" ]; then
    echo "Aborted."
    exit 1
fi

echo "[INFO] Terminating active connections to '${DB_NAME}'..."
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" || true

echo "[INFO] Dropping and recreating database '${DB_NAME}'..."
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

echo "[INFO] Restoring database content..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

echo "[SUCCESS] Database restoration complete at $(date)."
