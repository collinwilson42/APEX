"""
═══════════════════════════════════════════════════════════════════════════════
APEX PyWebView Launcher
Family F: SYSTEM_INFRASTRUCTURE_BRIDGE | PC-249, PC-250
═══════════════════════════════════════════════════════════════════════════════

Desktop application wrapper using PyWebView.
Launches APEX as a native-feeling desktop app.

Features:
- Frameless window option
- Portrait orientation detection
- Positioned in top 2/3 of screen
- JS Bridge for Python function exposure
"""

import webview
import threading
import time
import sys
import os
import ctypes

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask_apex import app


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    'title': 'APEX - Adaptive Platform for Evolving eXecution',
    'width': 1440,       # Default width
    'height': None,      # Will be calculated as 2/3 of screen
    'min_width': 800,
    'min_height': 600,
    'frameless': False,  # Set True for borderless window
    'easy_drag': True,
    'text_select': False,
    'url': 'http://localhost:5000'
}


# ═══════════════════════════════════════════════════════════════════════════════
# JS API BRIDGE (PC-250)
# ═══════════════════════════════════════════════════════════════════════════════

class ApexAPI:
    """
    Python functions exposed to JavaScript via pywebview.api
    """
    
    def __init__(self):
        self.window = None
    
    def set_window(self, window):
        self.window = window
    
    def get_screen_info(self):
        """Get screen dimensions"""
        try:
            # Windows-specific
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            
            return {
                'width': screen_width,
                'height': screen_height,
                'orientation': 'portrait' if screen_height > screen_width else 'landscape'
            }
        except:
            return {
                'width': 1920,
                'height': 1080,
                'orientation': 'landscape'
            }
    
    def minimize(self):
        """Minimize window"""
        if self.window:
            self.window.minimize()
    
    def maximize(self):
        """Maximize/restore window"""
        if self.window:
            self.window.toggle_fullscreen()
    
    def close(self):
        """Close window"""
        if self.window:
            self.window.destroy()
    
    def set_title(self, title):
        """Set window title"""
        if self.window:
            self.window.set_title(title)
    
    def log(self, message):
        """Log message to Python console"""
        print(f'[APEX JS] {message}')
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# WINDOW POSITIONING (PC-249)
# ═══════════════════════════════════════════════════════════════════════════════

def get_window_geometry():
    """
    Calculate window size and position for top 2/3 of screen.
    Optimized for vertical (portrait) monitor orientation.
    """
    try:
        user32 = ctypes.windll.user32
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
    except:
        screen_width = 1920
        screen_height = 1080
    
    # For portrait orientation, use full width
    # For landscape, use configured width
    is_portrait = screen_height > screen_width
    
    if is_portrait:
        window_width = screen_width
        window_height = int(screen_height * 0.6667)  # Top 2/3
        x = 0
        y = 0
    else:
        window_width = min(CONFIG['width'], screen_width)
        window_height = int(screen_height * 0.6667)
        x = (screen_width - window_width) // 2
        y = 0
    
    return {
        'width': window_width,
        'height': window_height,
        'x': x,
        'y': y,
        'is_portrait': is_portrait
    }


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK SERVER THREAD
# ═══════════════════════════════════════════════════════════════════════════════

def start_flask():
    """Run Flask in a separate thread"""
    # Suppress Flask's default logging for cleaner output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LAUNCHER
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print('═══════════════════════════════════════════════════════════════')
    print('  APEX Desktop Application')
    print('  Version 11.0.0 - Phase 1 Quad Run')
    print('═══════════════════════════════════════════════════════════════')
    
    # Get window geometry
    geometry = get_window_geometry()
    
    print(f'  Screen: {"Portrait" if geometry["is_portrait"] else "Landscape"}')
    print(f'  Window: {geometry["width"]}x{geometry["height"]} at ({geometry["x"]}, {geometry["y"]})')
    print('═══════════════════════════════════════════════════════════════')
    
    # Create API instance
    api = ApexAPI()
    
    # Start Flask server in background thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Wait for Flask to start
    time.sleep(1)
    
    # Create PyWebView window
    window = webview.create_window(
        title=CONFIG['title'],
        url=CONFIG['url'],
        width=geometry['width'],
        height=geometry['height'],
        x=geometry['x'],
        y=geometry['y'],
        min_size=(CONFIG['min_width'], CONFIG['min_height']),
        frameless=CONFIG['frameless'],
        easy_drag=CONFIG['easy_drag'],
        text_select=CONFIG['text_select'],
        js_api=api
    )
    
    # Give API access to window
    api.set_window(window)
    
    # Start webview (blocking)
    webview.start(debug=True)


if __name__ == '__main__':
    main()
