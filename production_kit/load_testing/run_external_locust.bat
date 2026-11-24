@echo off
REM ==============================================================================
REM LABORA External Load Generator Runner (Windows)
REM Run this script on a separate physical machine on the same LAN as LABORA
REM ==============================================================================

set TARGET_URL=%~1
if "%TARGET_URL%"=="" set TARGET_URL=http://127.0.0.1

set STAGE=%~2
if "%STAGE%"=="" set STAGE=stage1_25users

set USERS=%~3
if "%USERS%"=="" set USERS=25

set SPAWN_RATE=%~4
if "%SPAWN_RATE%"=="" set SPAWN_RATE=5

set DURATION=%~5
if "%DURATION%"=="" set DURATION=90s

if not exist results mkdir results

echo ==========================================================
echo  Starting LABORA Institutional Load Test: %STAGE%
echo  Target URL:   %TARGET_URL%
echo  Users:        %USERS%
echo  Spawn Rate:   %SPAWN_RATE%/s
echo  Duration:     %DURATION%
echo ==========================================================

set LOCUST_INSECURE_SSL=true
set LOAD_TEST_STUDENT_COUNT=1000
set LOAD_TEST_PASSWORD=LoadTest123!

locust -f locustfile.py ^
  --headless ^
  --host "%TARGET_URL%" ^
  --users %USERS% ^
  --spawn-rate %SPAWN_RATE% ^
  --run-time %DURATION% ^
  --csv "results/%STAGE%" ^
  --html "results/%STAGE%.html" ^
  --only-summary

echo ==========================================================
echo  Test completed. Results saved in results/%STAGE%*
echo ==========================================================
