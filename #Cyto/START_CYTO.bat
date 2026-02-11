@echo off
echo ════════════════════════════════════════════════════════════════
echo  TORRA / CYTO - 4D Temporal Database
echo ════════════════════════════════════════════════════════════════
echo.
echo  Starting on http://localhost:5000
echo.
echo ════════════════════════════════════════════════════════════════
echo.

cd /d %~dp0
set PYTHONPATH=%~dp0
C:\Python312\python.exe run.py

pause
