@echo off
echo ================================================================
echo CYTO LIVE ANCHOR STREAMING - QUICK TEST
echo ================================================================
echo.
echo This will start CYTO server with live anchor support
echo.
echo After server starts:
echo 1. Open http://localhost:5000 in browser
echo 2. Open another terminal and run: python cyto_bridge.py --manual
echo 3. Type anchor: v1.5 r5 d.TEST a8 c8 t.NOW
echo 4. Watch it appear in real-time!
echo.
echo ================================================================
echo Starting CYTO Server...
echo ================================================================
echo.

python app.py

pause
