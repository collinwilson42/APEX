"""
MT5 META AGENT V3.1 - SCREENSHOT CAPTURE SYSTEM
Captures MT5 chart screenshots at :00/:15/:30/:45 marks
Saves to screenshots/ directory with timestamp naming
Uses PIL ImageGrab for reliable multi-monitor support
"""

import pyautogui
from PIL import ImageGrab
import time
import os
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
SCREENSHOT_DIR = Path("screenshots")
SYMBOL = "XAUG26.sim"
TIMEFRAME = "15m"

# Screen capture settings
MONITOR_NUMBER = None  # Set to 1, 2, 3, etc. to capture specific monitor (None = auto)
CAPTURE_REGION = None  # None = full screen, or (x, y, width, height) for specific region
QUALITY = 95  # JPEG quality (1-100)

# Capture timing
CAPTURE_INTERVALS = [0, 15, 30, 45]  # Minutes past the hour

class ScreenshotCapture:
    def __init__(self):
        self.screenshot_dir = SCREENSHOT_DIR
        self.last_capture_time = None
        self.capture_count = 0
        
        # Create screenshots directory
        self.screenshot_dir.mkdir(exist_ok=True)
        
    def should_capture(self) -> bool:
        """Check if we should capture at current time"""
        now = datetime.now()
        current_minute = now.minute
        
        # Check if we're at a capture interval
        if current_minute not in CAPTURE_INTERVALS:
            return False
        
        # Check if we already captured this interval
        if self.last_capture_time:
            # If less than 60 seconds since last capture, skip
            time_diff = (now - self.last_capture_time).total_seconds()
            if time_diff < 60:
                return False
        
        return True
    
    def get_screenshot_filename(self, timestamp: datetime) -> str:
        """Generate screenshot filename with timestamp"""
        # Format: XAUG26_15m_2024-12-09_14-30-00.png
        filename = "{}_{}_{}".format(SYMBOL, TIMEFRAME, timestamp.strftime('%Y-%m-%d_%H-%M-%S'))
        filename += ".png"
        return str(self.screenshot_dir / filename)
    
    def capture_screen(self) -> tuple:
        """
        Capture screenshot and save to file
        
        Returns:
            Tuple of (filepath, timestamp)
        """
        timestamp = datetime.now()
        filepath = self.get_screenshot_filename(timestamp)
        
        try:
            # Capture screenshot using PIL ImageGrab (more reliable than pyautogui)
            if CAPTURE_REGION:
                # Capture specific region (manual coordinates)
                # CAPTURE_REGION should be (x, y, width, height)
                # Convert to PIL bbox format (x1, y1, x2, y2)
                x, y, w, h = CAPTURE_REGION
                bbox = (x, y, x + w, y + h)
                screenshot = ImageGrab.grab(bbox=bbox, all_screens=False)
                
            elif MONITOR_NUMBER is not None:
                # Capture specific monitor by number
                try:
                    from screeninfo import get_monitors
                    monitors = get_monitors()
                    
                    if MONITOR_NUMBER < 1 or MONITOR_NUMBER > len(monitors):
                        print("[ERROR] Monitor {} not found! Using primary monitor instead.".format(MONITOR_NUMBER))
                        screenshot = ImageGrab.grab(all_screens=False)
                    else:
                        m = monitors[MONITOR_NUMBER - 1]
                        print("[INFO] Capturing Monitor {} ({}x{} at {},{})".format(
                            MONITOR_NUMBER, m.width, m.height, m.x, m.y))
                        
                        # Convert to PIL bbox format (x1, y1, x2, y2)
                        bbox = (m.x, m.y, m.x + m.width, m.y + m.height)
                        screenshot = ImageGrab.grab(bbox=bbox, all_screens=False)
                        
                except ImportError:
                    print("[ERROR] screeninfo not installed. Install with: pip install screeninfo")
                    screenshot = ImageGrab.grab(all_screens=False)
                    
            else:
                # Capture primary monitor only (not all screens)
                screenshot = ImageGrab.grab(all_screens=False)
            
            # Save to file (PNG doesn't use quality parameter)
            if filepath.endswith('.png'):
                screenshot.save(filepath)
            else:
                screenshot.save(filepath, quality=QUALITY)
            
            self.last_capture_time = timestamp
            self.capture_count += 1
            
            # Get file size
            file_size = os.path.getsize(filepath)
            file_size_kb = file_size / 1024
            
            print("[OK] Screenshot captured: {}".format(filepath))
            print("  Size: {:.1f} KB".format(file_size_kb))
            print("  Time: {}".format(timestamp.strftime('%Y-%m-%d %H:%M:%S')))
            print("  Count: {}".format(self.capture_count))
            
            return filepath, timestamp
            
        except Exception as e:
            print("[ERROR] Screenshot capture failed: {}".format(e))
            return None, None
    
    def wait_for_next_interval(self):
        """Calculate and wait until next capture interval"""
        now = datetime.now()
        current_minute = now.minute
        
        # Find next capture minute
        next_minute = None
        for interval in CAPTURE_INTERVALS:
            if interval > current_minute:
                next_minute = interval
                break
        
        # If no interval found in current hour, use first interval of next hour
        if next_minute is None:
            next_minute = CAPTURE_INTERVALS[0]
            next_time = now.replace(hour=now.hour + 1, minute=next_minute, second=0, microsecond=0)
        else:
            next_time = now.replace(minute=next_minute, second=0, microsecond=0)
        
        # Calculate wait time
        wait_seconds = (next_time - now).total_seconds()
        
        print("\n[WAIT] Next capture at {}".format(next_time.strftime('%H:%M:%S')))
        print("   Waiting {:.0f} seconds...".format(wait_seconds))
        
        return wait_seconds
    
    def run_continuous(self):
        """Run continuous capture loop"""
        print("="*70)
        print("MT5 SCREENSHOT CAPTURE - RUNNING")
        print("="*70)
        print("Symbol: {}".format(SYMBOL))
        print("Timeframe: {}".format(TIMEFRAME))
        print("Intervals: {} minutes past hour".format(CAPTURE_INTERVALS))
        print("Save directory: {}".format(self.screenshot_dir.absolute()))
        print("Press Ctrl+C to stop")
        print("="*70 + "\n")
        
        try:
            while True:
                if self.should_capture():
                    filepath, timestamp = self.capture_screen()
                    
                    if filepath:
                        # Wait a few seconds before checking again
                        time.sleep(5)
                    
                else:
                    # Wait until next interval
                    wait_seconds = self.wait_for_next_interval()
                    time.sleep(min(wait_seconds, 30))  # Check every 30s max
                
        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("SCREENSHOT CAPTURE STOPPED")
            print("="*70)
            print("Total captures: {}".format(self.capture_count))
            print("Screenshots saved to: {}".format(self.screenshot_dir.absolute()))
            print("="*70)
    
    def test_capture(self):
        """Test single screenshot capture"""
        print("="*70)
        print("TESTING SCREENSHOT CAPTURE")
        print("="*70)
        print("\nCapturing screenshot in 3 seconds...")
        print("Make sure MT5 chart is visible!\n")
        
        for i in range(3, 0, -1):
            print("{}...".format(i))
            time.sleep(1)
        
        filepath, timestamp = self.capture_screen()
        
        if filepath:
            print("\n[OK] Test successful!")
            print("  Screenshot saved: {}".format(filepath))
            print("\nOpen the file to verify it captured the MT5 chart correctly.")
            print("If the region is wrong, update CAPTURE_REGION in the code.")
        else:
            print("\n[ERROR] Test failed!")
        
        print("="*70)

def configure_capture_region():
    """Interactive tool to configure capture region"""
    print("="*70)
    print("CAPTURE REGION CONFIGURATION")
    print("="*70)
    print("\nMove your mouse to the TOP-LEFT corner of the MT5 chart")
    print("Press Ctrl+C when ready...\n")
    
    try:
        while True:
            x, y = pyautogui.position()
            print("\rCurrent position: X={}, Y={}    ".format(x, y), end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        top_left = pyautogui.position()
        print("\n\n[OK] Top-left corner: X={}, Y={}".format(top_left[0], top_left[1]))
    
    print("\nNow move to the BOTTOM-RIGHT corner of the MT5 chart")
    print("Press Ctrl+C when ready...\n")
    
    try:
        while True:
            x, y = pyautogui.position()
            print("\rCurrent position: X={}, Y={}    ".format(x, y), end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        bottom_right = pyautogui.position()
        print("\n\n[OK] Bottom-right corner: X={}, Y={}".format(bottom_right[0], bottom_right[1]))
    
    # Calculate region
    x = top_left[0]
    y = top_left[1]
    width = bottom_right[0] - top_left[0]
    height = bottom_right[1] - top_left[1]
    
    print("\n" + "="*70)
    print("REGION CALCULATED")
    print("="*70)
    print("Top-left: ({}, {})".format(x, y))
    print("Size: {} x {}".format(width, height))
    print("\nAdd this to your code:")
    print("CAPTURE_REGION = ({}, {}, {}, {})".format(x, y, width, height))
    print("="*70)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "test":
            # Test mode - single capture
            capturer = ScreenshotCapture()
            capturer.test_capture()
            
        elif mode == "configure":
            # Configuration mode - set capture region
            configure_capture_region()
            
        else:
            print("Unknown mode: {}".format(mode))
            print("Usage: python screenshot_capture.py [test|configure]")
    else:
        # Normal mode - continuous capture
        capturer = ScreenshotCapture()
        capturer.run_continuous()
