#!/bin/bash
# ==============================================================================
# LABORA Production PostgreSQL Automated Backup Script
# Creates compressed, checksummed backups and rotates older copies
# ==============================================================================

set -euo pipefail

BACKUP_DIR="/var/backups/labora"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="labora_backup_${TIMESTAMP}.sql.gz"
CONTAINER_NAME="labora-db"
DB_USER="${POSTGRES_USER:-labora_admin}"
DB_NAME="${POSTGRES_DB:-labora}"
RETENTION_DAYS=30

mkdir -p "${BACKUP_DIR}"

echo "[INFO] Starting database backup at $(date)..."

# Execute pg_dump inside the PostgreSQL container and compress on the fly
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip -9 > "${BACKUP_DIR}/${FILENAME}"

# Generate SHA256 checksum for integrity verification
sha256sum "${BACKUP_DIR}/${FILENAME}" > "${BACKUP_DIR}/${FILENAME}.sha256"

# Verify that file is non-empty
FILESIZE=$(stat -c%s "${BACKUP_DIR}/${FILENAME}")
if [ "${FILESIZE}" -lt 1024 ]; then
    echo "[ERROR] Backup file is suspiciously small (${FILESIZE} bytes). Aborting!"
    exit 1
fi

echo "[INFO] Successfully created backup: ${BACKUP_DIR}/${FILENAME} (${FILESIZE} bytes)"

# Prune backups older than RETENTION_DAYS
echo "[INFO] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "labora_backup_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -delete

echo "[INFO] Backup process completed successfully."
