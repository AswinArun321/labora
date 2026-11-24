#!/usr/bin/env bash
# ==============================================================================
# LABORA External Load Generator Runner (Linux / macOS)
# Run this script on a separate physical machine on the same LAN as LABORA
# ==============================================================================
set -euo pipefail

TARGET_URL="${1:-http://127.0.0.1}"
STAGE="${2:-stage1_25users}"
USERS="${3:-25}"
SPAWN_RATE="${4:-5}"
DURATION="${5:-90s}"

mkdir -p results

echo "=========================================================="
echo " Starting LABORA Institutional Load Test: ${STAGE}"
echo " Target URL:   ${TARGET_URL}"
echo " Users:        ${USERS}"
echo " Spawn Rate:   ${SPAWN_RATE}/s"
echo " Duration:     ${DURATION}"
echo "=========================================================="

export LOCUST_INSECURE_SSL="true"
export LOAD_TEST_STUDENT_COUNT="1000"
export LOAD_TEST_PASSWORD="LoadTest123!"

locust -f locustfile.py \
  --headless \
  --host "${TARGET_URL}" \
  --users "${USERS}" \
  --spawn-rate "${SPAWN_RATE}" \
  --run-time "${DURATION}" \
  --csv "results/${STAGE}" \
  --html "results/${STAGE}.html" \
  --only-summary

echo "=========================================================="
echo " Test completed. Results saved in results/${STAGE}*"
echo "=========================================================="
