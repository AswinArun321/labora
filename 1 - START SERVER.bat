@echo off
title LABORA Server (keep this window open)
cd /d "%~dp0server\backend"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo.
  echo  Python 3.10 or newer is required.
  echo  Install it from https://www.python.org/downloads/
  echo  and tick "Add python.exe to PATH" during setup, then run this file again.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment ^(first run only^)...
  %PY% -m venv .venv || goto :fail
)
set "VPY=%cd%\.venv\Scripts\python.exe"

echo Installing packages ^(first run takes about a minute^)...
"%VPY%" -m pip install -q --disable-pip-version-check -r requirements-test.txt || goto :fail

"%VPY%" manage.py migrate -v0 || goto :fail
if not exist ".seeded" (
  "%VPY%" manage.py seed_demo --secure-langs c || goto :fail
  echo done> .seeded
)

set CODE_EXECUTOR=local
echo.
echo  ============================================================
echo   LABORA is running at  http://127.0.0.1:8000
echo.
echo   Logins:  admin / admin123
echo            teacher / teacher123
echo            student1 ... student4 / student123
echo.
echo   Next: double-click "2 - START SECURE BROWSER.bat"
echo         or open http://127.0.0.1:8000 in Chrome / Edge.
echo   Close this window to stop the server.
echo  ============================================================
echo.
start "" http://127.0.0.1:8000
"%VPY%" manage.py runserver 127.0.0.1:8000 --noreload
goto :eof

:fail
echo.
echo  Something went wrong above. Take a screenshot of this window.
pause
