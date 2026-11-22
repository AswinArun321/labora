@echo off
cd /d "%~dp0server\backend"
del /q db.sqlite3 .seeded 2>nul
echo Demo data cleared. Run "1 - START SERVER.bat" again.
pause
