@echo off
echo ============================================================
echo HEXADIC SYSTEM - QUICK TEST
echo ============================================================
echo.

cd /d "C:\Users\cwils\OneDrive\Desktop\Adaptive MT5 Meta Agent\V11\_AI_Context_Export\#CodeBase"

echo [1/2] Running hexadic_quickstart.py...
echo.
python hexadic_quickstart.py

echo.
echo [2/2] Testing storage directly...
python -c "from hexadic_storage import HexadicStorage; s=HexadicStorage(); print(f'\nAnchors in DB: {len(s.search_anchors())}')"

echo.
echo ============================================================
echo TEST COMPLETE
echo ============================================================
echo.
echo NEXT: Run init2.py to start Flask server with hexadic API
echo.
pause
