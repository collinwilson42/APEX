"""
CYTO BRIDGE - Capture Inline Anchors from Claude Sessions

This script monitors Claude conversations and streams inline anchors to CYTO.

USAGE OPTIONS:

1. Manual Input (Testing):
   python cyto_bridge.py --manual

2. Monitor Clipboard:
   python cyto_bridge.py --clipboard
   (Copy anchor from Claude, it auto-sends to CYTO)

3. File Watcher:
   python cyto_bridge.py --watch /path/to/session_log.txt
   (Watches file for new anchors)

4. API Mode (for integrations):
   Just POST to http://your-vps:5000/api/anchor/create
"""

import argparse
import re
import time
from datetime import datetime
import socketio
import pyperclip  # pip install pyperclip

# CYTO server configuration
CYTO_SERVER = 'http://localhost:5000'  # Change to VPS IP when deployed


class CytoBridge:
    """Bridge between Claude sessions and CYTO database."""
    
    def __init__(self, server_url=CYTO_SERVER):
        self.server_url = server_url
        self.socket = socketio.Client()
        self.connected = False
        self.last_clipboard = ""
        
        # Setup socket event handlers
        self.socket.on('connect', self.on_connect)
        self.socket.on('disconnect', self.on_disconnect)
        self.socket.on('anchor_added', self.on_anchor_added)
        self.socket.on('error', self.on_error)
    
    def on_connect(self):
        """Handle connection to CYTO."""
        self.connected = True
        print(f"✓ Connected to CYTO at {self.server_url}")
    
    def on_disconnect(self):
        """Handle disconnection."""
        self.connected = False
        print("✗ Disconnected from CYTO")
    
    def on_anchor_added(self, data):
        """Handle confirmation that anchor was added."""
        print(f"✨ Anchor live: {data['anchor_string']} (Station {data['station']}, {data['domain']})")
    
    def on_error(self, data):
        """Handle errors."""
        print(f"✗ Error: {data.get('message')}")
    
    def connect(self):
        """Connect to CYTO server."""
        try:
            self.socket.connect(self.server_url)
            print(f"📡 Connecting to CYTO...")
            time.sleep(1)  # Wait for connection
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
        return self.connected
    
    def send_anchor(self, anchor_string, source='manual'):
        """Send inline anchor to CYTO."""
        if not self.connected:
            print("✗ Not connected to CYTO")
            return False
        
        # Validate anchor format
        if not self.validate_anchor(anchor_string):
            print(f"✗ Invalid anchor format: {anchor_string}")
            return False
        
        # Send via WebSocket
        self.socket.emit('anchor_created', {
            'anchor_string': anchor_string.strip(),
            'timestamp': datetime.now().isoformat(),
            'source': source
        })
        
        print(f"📤 Sent: {anchor_string}")
        return True
    
    def validate_anchor(self, anchor_str):
        """Validate anchor string format."""
        pattern = r'v\d+\.\d+\s+r\d\s+d\.\w+\s+a\d\s+c\d\s+t\.\w+'
        return bool(re.match(pattern, anchor_str.strip()))
    
    def manual_mode(self):
        """Manual input mode - type anchors directly."""
        print("\n" + "="*60)
        print("MANUAL INPUT MODE")
        print("="*60)
        print("Enter inline anchors (or 'quit' to exit)")
        print("Format: v1.5 r5 d.DOMAIN a8 c8 t.NOW")
        print("="*60 + "\n")
        
        while True:
            try:
                anchor = input("Anchor: ").strip()
                
                if anchor.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not anchor:
                    continue
                
                self.send_anchor(anchor, source='manual')
                
            except KeyboardInterrupt:
                break
        
        print("\n✓ Exiting manual mode")
    
    def clipboard_mode(self):
        """Monitor clipboard for new anchors."""
        print("\n" + "="*60)
        print("CLIPBOARD MONITOR MODE")
        print("="*60)
        print("Copy inline anchors from Claude - they'll auto-send to CYTO")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        try:
            while True:
                # Get clipboard content
                clipboard = pyperclip.paste()
                
                # Check if it's new and looks like an anchor
                if clipboard != self.last_clipboard:
                    if self.validate_anchor(clipboard):
                        self.send_anchor(clipboard, source='clipboard')
                        self.last_clipboard = clipboard
                
                time.sleep(0.5)  # Check every 500ms
                
        except KeyboardInterrupt:
            print("\n✓ Stopped clipboard monitor")
    
    def file_watch_mode(self, filepath):
        """Watch a file for new anchors."""
        print(f"\n📁 Watching file: {filepath}")
        print("Press Ctrl+C to stop\n")
        
        try:
            with open(filepath, 'r') as f:
                # Start from end of file
                f.seek(0, 2)
                
                while True:
                    line = f.readline()
                    
                    if line:
                        # Check if line contains an anchor
                        if self.validate_anchor(line):
                            self.send_anchor(line, source='file_watch')
                    else:
                        time.sleep(0.5)
                        
        except KeyboardInterrupt:
            print("\n✓ Stopped file watcher")
        except FileNotFoundError:
            print(f"✗ File not found: {filepath}")
    
    def disconnect(self):
        """Disconnect from CYTO."""
        if self.connected:
            self.socket.disconnect()


def main():
    parser = argparse.ArgumentParser(description='CYTO Bridge - Stream anchors from Claude to CYTO')
    parser.add_argument('--manual', action='store_true', help='Manual input mode')
    parser.add_argument('--clipboard', action='store_true', help='Monitor clipboard for anchors')
    parser.add_argument('--watch', type=str, help='Watch file for new anchors')
    parser.add_argument('--server', type=str, default=CYTO_SERVER, help='CYTO server URL')
    
    args = parser.parse_args()
    
    # Create bridge
    bridge = CytoBridge(server_url=args.server)
    
    # Connect to CYTO
    if not bridge.connect():
        print("✗ Failed to connect to CYTO. Is the server running?")
        return
    
    # Run selected mode
    try:
        if args.manual:
            bridge.manual_mode()
        elif args.clipboard:
            bridge.clipboard_mode()
        elif args.watch:
            bridge.file_watch_mode(args.watch)
        else:
            # Default to manual
            bridge.manual_mode()
    finally:
        bridge.disconnect()


if __name__ == '__main__':
    main()
