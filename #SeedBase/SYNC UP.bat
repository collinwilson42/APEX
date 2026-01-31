@echo off
:: Ensure we are in the root folder
cd /d "C:\Users\colli\Downloads\#CodeBase"

echo ==========================================
echo      APEX CODEBASE SYNC (SMART SAVE)
echo ==========================================

:: 1. Safety Check: Ensure .gitignore exists so we don't accidentally upload DBs
if not exist .gitignore (
    echo [WARNING] .gitignore not found! Creating safety net...
    echo *.db >> .gitignore
    echo __pycache__/ >> .gitignore
    echo .env >> .gitignore
)

:: 2. Add Changes (Git will now automatically skip .db files)
echo [1/3] Scanning for changes...
git add .

:: 3. Commit with Timestamp
echo [2/3] Saving snapshot...
git commit -m "Sync: %date% %time%"

:: 4. Push to GitHub
echo [3/3] Uploading to Cloud...
git push origin main

:: 5. Success/Fail Check
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Sync Failed. Check your internet or login.
    echo (If it says 'nothing to commit', that just means you haven't changed anything yet.)
    pause
) else (
    echo.
    echo [SUCCESS] Codebase is safe and synced.
    timeout /t 3 >nul
)