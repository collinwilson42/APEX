#!/usr/bin/env python3
"""
V6 Intelligence Database - System Launcher (app.py)
Starts both Flask app (flask_app.py) and Webhook server (unified_webhook_server.py)
"""

import subprocess
import sys
import os
import time
import signal

def check_file_exists(filepath, description):
    """Check if a required file exists"""
    if os.path.exists(filepath):
        print(f"[CHECK] {filepath} found ✓")
        return True
    else:
        print(f"[ERROR] {filepath} not found ✗")
        print(f"        {description}")
        return False

def main():
    """Main launcher function"""
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  V6 INTELLIGENCE DATABASE - SYSTEM STARTUP                 ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    
    # Check required files
    required_files = {
        'unified_webhook_server.py': 'Webhook server that receives TradingView alerts',
        'flask_app.py': 'Flask application that serves the web interface',
        'config.py': 'Configuration file',
        'templates/chart_data.html': 'V6 database template',
    }
    
    all_files_exist = True
    for filepath, description in required_files.items():
        if not check_file_exists(filepath, description):
            all_files_exist = False
    
    if not all_files_exist:
        print()
        print("[ERROR] Missing required files. Cannot start system.")
        print("        Please ensure all files are in the correct locations.")
        sys.exit(1)
    
    print()
    print("[START] Launching webhook server on port 6789...")
    webhook_process = subprocess.Popen(
        [sys.executable, 'unified_webhook_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Give webhook server time to start
    time.sleep(2)
    
    print("[START] Launching Flask app on port 5000...")
    flask_process = subprocess.Popen(
        [sys.executable, 'flask_app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  SYSTEM READY                                              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()
    print("Access URLs:")
    print("  📊 Dashboard:      http://localhost:5000/")
    print("  📈 V6 Database:    http://localhost:5000/chart-data")
    print("  ✅ Flask Health:   http://localhost:5000/api/health")
    print("  ✅ Webhook Health: http://localhost:6789/api/health")
    print()
    print("Press Ctrl+C to stop all services")
    print("═" * 62)
    print()
    
    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully"""
        print()
        print("╔════════════════════════════════════════════════════════════╗")
        print("║  SHUTTING DOWN                                             ║")
        print("╚════════════════════════════════════════════════════════════╝")
        print()
        print("[STOP] Terminating webhook server...")
        webhook_process.terminate()
        
        print("[STOP] Terminating Flask app...")
        flask_process.terminate()
        
        # Wait for processes to terminate
        try:
            webhook_process.wait(timeout=5)
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("[WARN] Forcing shutdown...")
            webhook_process.kill()
            flask_process.kill()
        
        print()
        print("✅ System stopped successfully")
        print("═" * 62)
        sys.exit(0)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Keep main process alive and monitor subprocesses
        while True:
            # Check if either process has died
            if webhook_process.poll() is not None:
                print()
                print("[ERROR] Webhook server died unexpectedly!")
                print("[ERROR] Check unified_webhook_server.py for errors")
                flask_process.terminate()
                sys.exit(1)
            
            if flask_process.poll() is not None:
                print()
                print("[ERROR] Flask app died unexpectedly!")
                print("[ERROR] Check flask_app.py for errors")
                webhook_process.terminate()
                sys.exit(1)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()
