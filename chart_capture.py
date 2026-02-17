"""
CHART CAPTURE — Headless Plotly Export via Playwright
=====================================================
Seed 23: Internal Chart Capture

Instead of screenshotting the monitor (which captures whatever window
is in focus), this module spins up a headless Chromium browser, loads
the Apex app, and exports charts directly via Plotly.toImage().

This guarantees the AI always sees the actual trading chart, regardless
of what's on the user's screen.

Usage:
    from chart_capture import capture_chart
    
    b64_png = capture_chart("15m")             # quick single chart
    b64_png = capture_chart("1h", width=1400)  # wider 1h chart
    
    # Or capture both at once (reuses the same browser page):
    images = capture_charts_batch(["15m", "1h"])

Requirements:
    pip install playwright
    playwright install chromium

Falls back to mss monitor screenshot if Playwright is unavailable.
"""

import os
import sys
import json
import time
import base64
import logging
from typing import Optional, Dict, List

# ── Playwright (preferred) ──
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ── MSS fallback ──
try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# ── Config ──
APEX_URL = os.getenv("APEX_URL", "http://localhost:5000")
CHART_RENDER_WAIT_MS = 3000   # Wait for Plotly to finish rendering
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 500


# ═══════════════════════════════════════════════════════════════════════════
# PLAYWRIGHT CAPTURE — The clean way
# ═══════════════════════════════════════════════════════════════════════════

def capture_chart(timeframe: str = "15m",
                  width: int = DEFAULT_WIDTH,
                  height: int = DEFAULT_HEIGHT,
                  symbol: str = None,
                  include_matrix: bool = False) -> Optional[str]:
    """
    Capture a single chart as base64 PNG via headless Playwright.
    
    Args:
        timeframe: "15m" or "1h"
        width: Export width in pixels
        height: Export height in pixels
        symbol: Optional symbol filter (future: navigate to correct tab)
        include_matrix: If True, also capture the Markov matrix panel
    
    Returns:
        Base64-encoded PNG string, or None on failure
    """
    if not HAS_PLAYWRIGHT:
        logging.warning("Playwright not installed — falling back to mss screenshot")
        return _mss_fallback()
    
    chart_id = f"chart-{timeframe}"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            
            # Load Apex
            page.goto(APEX_URL, wait_until="networkidle")
            
            # Click the algo tab if needed (the second tab is typically the algo view)
            _navigate_to_algo_view(page)
            
            # Wait for Plotly charts to render
            page.wait_for_selector(f"#{chart_id} .plot-container", timeout=10000)
            page.wait_for_timeout(CHART_RENDER_WAIT_MS)
            
            # Export via Plotly.toImage()
            b64 = page.evaluate(f"""
                async () => {{
                    const chartEl = document.getElementById('{chart_id}');
                    if (!chartEl || !chartEl.data) return null;
                    
                    try {{
                        const dataUrl = await Plotly.toImage(chartEl, {{
                            format: 'png',
                            width: {width},
                            height: {height},
                            scale: 2
                        }});
                        // Strip "data:image/png;base64," prefix
                        return dataUrl.split(',')[1];
                    }} catch(e) {{
                        return null;
                    }}
                }}
            """)
            
            browser.close()
            
            if b64:
                logging.info(f"📸 Chart captured: {chart_id} ({len(b64) // 1024}KB) via Playwright")
                return b64
            else:
                logging.error(f"📸 Plotly.toImage() returned null for {chart_id}")
                return None
                
    except Exception as e:
        logging.error(f"📸 Playwright capture failed: {e}")
        return None


def capture_charts_batch(timeframes: List[str] = None,
                         width: int = DEFAULT_WIDTH,
                         height: int = DEFAULT_HEIGHT,
                         symbol: str = None) -> Dict[str, Optional[str]]:
    """
    Capture multiple charts in a single browser session (more efficient).
    
    Args:
        timeframes: List of timeframes, e.g. ["15m", "1h"]. Defaults to both.
        width/height: Export dimensions
        symbol: Optional symbol filter
    
    Returns:
        Dict mapping timeframe → base64 PNG (or None on failure)
    """
    if timeframes is None:
        timeframes = ["15m", "1h"]
    
    results = {tf: None for tf in timeframes}
    
    if not HAS_PLAYWRIGHT:
        logging.warning("Playwright not installed — falling back to mss screenshot")
        fallback = _mss_fallback()
        for tf in timeframes:
            results[tf] = fallback
        return results
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            
            # Load Apex once
            page.goto(APEX_URL, wait_until="networkidle")
            _navigate_to_algo_view(page)
            
            # Wait for charts
            page.wait_for_timeout(CHART_RENDER_WAIT_MS)
            
            # Export each chart
            for tf in timeframes:
                chart_id = f"chart-{tf}"
                try:
                    b64 = page.evaluate(f"""
                        async () => {{
                            const chartEl = document.getElementById('{chart_id}');
                            if (!chartEl || !chartEl.data) return null;
                            
                            try {{
                                const dataUrl = await Plotly.toImage(chartEl, {{
                                    format: 'png',
                                    width: {width},
                                    height: {height},
                                    scale: 2
                                }});
                                return dataUrl.split(',')[1];
                            }} catch(e) {{
                                return null;
                            }}
                        }}
                    """)
                    results[tf] = b64
                    if b64:
                        logging.info(f"📸 {chart_id}: {len(b64) // 1024}KB")
                except Exception as e:
                    logging.error(f"📸 {chart_id} export failed: {e}")
            
            browser.close()
            
    except Exception as e:
        logging.error(f"📸 Batch capture failed: {e}")
    
    return results


def capture_full_view(width: int = 1600, height: int = 1000) -> Optional[str]:
    """
    Capture the entire Apex algo view as a screenshot (not just Plotly export).
    Useful for giving Claude the full context including matrices and indicators.
    """
    if not HAS_PLAYWRIGHT:
        return _mss_fallback()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height})
            
            page.goto(APEX_URL, wait_until="networkidle")
            _navigate_to_algo_view(page)
            page.wait_for_timeout(CHART_RENDER_WAIT_MS)
            
            # Screenshot the full page
            png_bytes = page.screenshot(type="png", full_page=False)
            b64 = base64.standard_b64encode(png_bytes).decode("utf-8")
            
            browser.close()
            
            logging.info(f"📸 Full view captured: {len(b64) // 1024}KB")
            return b64
            
    except Exception as e:
        logging.error(f"📸 Full view capture failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# NAVIGATION HELPER
# ═══════════════════════════════════════════════════════════════════════════

def _navigate_to_algo_view(page):
    """
    Navigate to the algo trading view within the Apex app.
    The app uses tab-based navigation — the algo view is the second tab
    (or the tab containing chart-15m / chart-1h elements).
    """
    try:
        # Check if we're already on the algo view
        already = page.evaluate("""
            () => !!document.getElementById('chart-15m')
        """)
        if already:
            return
        
        # Try clicking the algo tab — look for tabs containing "Algorithm" or "Algo"
        tabs = page.query_selector_all('.tab-item, .nav-tab, [class*="tab"]')
        for tab in tabs:
            text = tab.inner_text()
            if 'algorithm' in text.lower() or 'algo' in text.lower():
                tab.click()
                page.wait_for_timeout(1000)
                return
        
        # Fallback: click the second tab (index 1)
        if len(tabs) > 1:
            tabs[1].click()
            page.wait_for_timeout(1000)
            
    except Exception as e:
        logging.warning(f"Algo view navigation: {e} (may already be on correct view)")


# ═══════════════════════════════════════════════════════════════════════════
# MSS FALLBACK — Legacy monitor screenshot
# ═══════════════════════════════════════════════════════════════════════════

def _mss_fallback(region=None) -> Optional[str]:
    """Fallback to mss monitor capture if Playwright unavailable."""
    if not HAS_MSS:
        logging.error("Neither Playwright nor mss available — cannot capture")
        return None
    
    try:
        with mss.mss() as sct:
            monitor = ({"left": region[0], "top": region[1],
                        "width": region[2], "height": region[3]}
                       if region else sct.monitors[1])
            shot = sct.grab(monitor)
            png = mss.tools.to_png(shot.rgb, shot.size)
            return base64.standard_b64encode(png).decode("utf-8")
    except Exception as e:
        logging.error(f"MSS fallback failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# FLASK ENDPOINT (register in init2.py)
# ═══════════════════════════════════════════════════════════════════════════

def register_capture_routes(app):
    """
    Register chart capture API endpoints.
    Call this from init2.py: register_capture_routes(app)
    """
    from flask import jsonify, request
    
    @app.route('/api/chart-capture/<timeframe>')
    def api_chart_capture(timeframe):
        """GET /api/chart-capture/15m → { "image": "base64...", "method": "playwright" }"""
        if timeframe not in ("15m", "1h"):
            return jsonify({"error": "Invalid timeframe. Use '15m' or '1h'"}), 400
        
        width = request.args.get('width', DEFAULT_WIDTH, type=int)
        height = request.args.get('height', DEFAULT_HEIGHT, type=int)
        
        b64 = capture_chart(timeframe, width=width, height=height)
        if b64:
            return jsonify({
                "image": b64,
                "timeframe": timeframe,
                "method": "playwright" if HAS_PLAYWRIGHT else "mss",
                "size_kb": len(b64) // 1024
            })
        else:
            return jsonify({"error": "Chart capture failed"}), 500
    
    @app.route('/api/chart-capture/full')
    def api_full_capture():
        """GET /api/chart-capture/full → full algo view screenshot"""
        b64 = capture_full_view()
        if b64:
            return jsonify({
                "image": b64,
                "method": "playwright" if HAS_PLAYWRIGHT else "mss",
                "size_kb": len(b64) // 1024
            })
        else:
            return jsonify({"error": "Full capture failed"}), 500


# ═══════════════════════════════════════════════════════════════════════════
# CLI TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("  CHART CAPTURE TEST")
    print(f"  Playwright: {'✓' if HAS_PLAYWRIGHT else '✗ (pip install playwright && playwright install chromium)'}")
    print(f"  MSS:        {'✓' if HAS_MSS else '✗'}")
    print(f"  Target:     {APEX_URL}")
    print("=" * 60)
    
    if not HAS_PLAYWRIGHT:
        print("\n⚠️  Install Playwright first:")
        print("    pip install playwright")
        print("    playwright install chromium")
        sys.exit(1)
    
    # Test single capture
    print("\n[1] Capturing 15m chart...")
    start = time.time()
    img = capture_chart("15m")
    elapsed = time.time() - start
    if img:
        print(f"    ✓ Success: {len(img) // 1024}KB in {elapsed:.1f}s")
        # Save test file
        with open("test_chart_15m.png", "wb") as f:
            f.write(base64.b64decode(img))
        print(f"    → Saved to test_chart_15m.png")
    else:
        print(f"    ✗ Failed after {elapsed:.1f}s")
    
    # Test batch capture
    print("\n[2] Batch capturing 15m + 1h...")
    start = time.time()
    batch = capture_charts_batch(["15m", "1h"])
    elapsed = time.time() - start
    for tf, data in batch.items():
        if data:
            print(f"    ✓ {tf}: {len(data) // 1024}KB")
        else:
            print(f"    ✗ {tf}: Failed")
    print(f"    Total: {elapsed:.1f}s")
    
    # Test full view
    print("\n[3] Capturing full algo view...")
    start = time.time()
    full = capture_full_view()
    elapsed = time.time() - start
    if full:
        print(f"    ✓ Success: {len(full) // 1024}KB in {elapsed:.1f}s")
        with open("test_full_view.png", "wb") as f:
            f.write(base64.b64decode(full))
        print(f"    → Saved to test_full_view.png")
    else:
        print(f"    ✗ Failed after {elapsed:.1f}s")
