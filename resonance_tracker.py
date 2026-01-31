#!/usr/bin/env python3
"""
KEYSTROKE CORRELATION ENGINE - RESONANCE TRACKER
Tracks typing patterns correlated with resonance frequency states

Features:
- Background keystroke monitoring (pynput)
- Auto-correlates with current frequency state
- Calculates typing speed, burst patterns, pause analysis
- Exports session data for Time Machine analysis
- Discovers optimal frequencies for flow states

Install: pip install pynput

Usage:
    python resonance_tracker.py start    # Start monitoring
    python resonance_tracker.py stop     # Stop and save
    python resonance_tracker.py analyze  # Analyze all sessions
"""

import json
import time
import statistics
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from collections import deque

# pynput import with graceful fallback
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError as e:
    PYNPUT_AVAILABLE = False
    PYNPUT_ERROR = str(e)


class ResonanceTracker:
    """
    Monitors keystrokes and correlates with resonance frequency states.
    Discovers optimal frequency patterns for different cognitive tasks.
    """
    
    def __init__(self, state_file: Optional[Path] = None, output_dir: Optional[Path] = None):
        """Initialize the resonance tracker"""
        
        # Check pynput availability
        if not PYNPUT_AVAILABLE:
            print(f"⚠ pynput not available: {PYNPUT_ERROR}")
            print("  Install: pip install pynput")
            self.available = False
            return
        
        self.available = True
        
        # Paths - auto-detect from system
        if state_file is None:
            import platform, os
            if platform.system() == "Windows":
                docs = Path(os.environ.get('USERPROFILE', '')) / 'Documents'
                base = docs / 'ResonanceSync'
            else:
                base = Path.home() / '.resonance_sync'
            state_file = base / "user_frequency_state.json"
            output_dir = base / "keystroke_logs"
        
        self.state_file = Path(state_file)
        self.output_dir = Path(output_dir) if output_dir else self.state_file.parent / "keystroke_logs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Monitoring state
        self.monitoring = False
        self.listener = None
        self.keystrokes: List[Dict] = []
        self.session_start: Optional[float] = None
        self.last_key_time: Optional[float] = None
        self.recent_keystrokes = deque(maxlen=500)
        
        # Session metadata
        self.session_id = None
        self.frequency_changes: List[Dict] = []
        self.last_frequency_state = None
        
        print(f"✓ ResonanceTracker initialized")
        print(f"  State file: {self.state_file}")
        print(f"  Output: {self.output_dir}")
    
    def get_current_frequency_state(self) -> Dict[str, Any]:
        """Read current frequency state from resonance system"""
        if not self.state_file.exists():
            return {'profile': 'baseline', 'frequency': None}
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except:
            return {'profile': 'baseline', 'frequency': None}
    
    def on_press(self, key):
        """Handle key press event"""
        now = time.time()
        
        # Get current frequency state
        freq_state = self.get_current_frequency_state()
        
        # Detect frequency changes
        if freq_state != self.last_frequency_state:
            self.frequency_changes.append({
                'timestamp': now,
                'from_profile': self.last_frequency_state.get('profile') if self.last_frequency_state else None,
                'to_profile': freq_state.get('profile'),
                'frequency': freq_state.get('frequency')
            })
            self.last_frequency_state = freq_state
            print(f"  → Frequency change detected: {freq_state.get('profile')}")
        
        # Calculate inter-key interval
        interval = now - self.last_key_time if self.last_key_time else 0
        self.last_key_time = now
        
        # Record keystroke
        keystroke_data = {
            'timestamp': now,
            'interval': interval,
            'profile': freq_state.get('profile'),
            'frequency': freq_state.get('frequency')
        }
        
        self.keystrokes.append(keystroke_data)
        self.recent_keystrokes.append(keystroke_data)
    
    def get_live_stats(self) -> Dict:
        """Get real-time statistics from recent keystrokes"""
        if len(self.recent_keystrokes) < 5:
            return {}
        
        recent = list(self.recent_keystrokes)
        intervals = [k['interval'] for k in recent if k['interval'] > 0]
        
        if not intervals:
            return {}
        
        # Calculate metrics
        duration = recent[-1]['timestamp'] - recent[0]['timestamp']
        cpm = (len(recent) / duration * 60) if duration > 0 else 0
        consistency = (1 - (statistics.stdev(intervals) / statistics.mean(intervals))) * 100 if len(intervals) > 1 else 0
        flow_score = cpm * (consistency / 100)
        
        return {
            'cpm': round(cpm, 1),
            'consistency': round(consistency, 1),
            'flow_score': round(flow_score, 1),
            'profile': recent[-1].get('profile', 'unknown')
        }
    
    def start_monitoring(self):
        """Start keystroke monitoring"""
        if not self.available:
            print("❌ pynput not available")
            return False
        
        if self.monitoring:
            print("⚠ Already monitoring")
            return False
        
        self.session_start = time.time()
        self.session_id = f"session_{int(self.session_start)}"
        self.keystrokes = []
        self.frequency_changes = []
        self.last_frequency_state = self.get_current_frequency_state()
        
        # Start listener
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        self.monitoring = True
        
        print(f"\n✓ Monitoring started")
        print(f"  Session ID: {self.session_id}")
        print(f"  Initial profile: {self.last_frequency_state.get('profile')}")
        print(f"\n  Press Ctrl+C to stop and analyze\n")
        return True
    
    def stop_monitoring(self) -> Optional[Path]:
        """Stop monitoring and save session data"""
        if not self.monitoring:
            print("⚠ Not currently monitoring")
            return None
        
        # Stop listener
        if self.listener:
            self.listener.stop()
            self.listener = None
        
        self.monitoring = False
        
        # Calculate session statistics
        duration = time.time() - self.session_start if self.session_start else 0
        total_keys = len(self.keystrokes)
        
        if total_keys < 2:
            print("⚠ Not enough keystrokes to analyze")
            return None
        
        # Calculate typing metrics
        intervals = [k['interval'] for k in self.keystrokes if k['interval'] > 0]
        cpm = (total_keys / duration * 60) if duration > 0 else 0
        consistency = (1 - (statistics.stdev(intervals) / statistics.mean(intervals))) * 100 if len(intervals) > 1 else 0
        flow_score = cpm * (consistency / 100)
        
        # Build session report
        session_data = {
            'session_id': self.session_id,
            'start_time': datetime.fromtimestamp(self.session_start).isoformat(),
            'duration_seconds': round(duration, 2),
            'total_keystrokes': total_keys,
            'metrics': {
                'cpm': round(cpm, 2),
                'consistency_pct': round(consistency, 2),
                'flow_score': round(flow_score, 2)
            },
            'frequency_changes': self.frequency_changes,
            'keystrokes': self.keystrokes
        }
        
        # Save to file
        output_file = self.output_dir / f"{self.session_id}.json"
        with open(output_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        print(f"\n" + "="*60)
        print(f"✓ SESSION COMPLETE")
        print(f"="*60)
        print(f"  Saved: {output_file}")
        print(f"  Duration: {duration:.1f}s")
        print(f"  Keystrokes: {total_keys}")
        print(f"  CPM: {cpm:.1f}")
        print(f"  Consistency: {consistency:.1f}%")
        print(f"  Flow Score: {flow_score:.1f}")
        print(f"  Frequency changes: {len(self.frequency_changes)}")
        
        return output_file
    
    def analyze_all_sessions(self) -> Dict:
        """Analyze all recorded sessions to find optimal frequencies"""
        session_files = list(self.output_dir.glob("session_*.json"))
        
        if not session_files:
            print("❌ No sessions found in:", self.output_dir)
            return {}
        
        print(f"\n{'='*60}")
        print(f"📊 ANALYZING {len(session_files)} SESSIONS")
        print(f"{'='*60}\n")
        
        # Aggregate by profile
        profile_stats = {}
        
        for session_file in session_files:
            with open(session_file, 'r') as f:
                session = json.load(f)
            
            # Group keystrokes by profile
            for keystroke in session.get('keystrokes', []):
                profile = keystroke.get('profile', 'unknown')
                
                if profile not in profile_stats:
                    profile_stats[profile] = {
                        'keystrokes': [],
                        'sessions': set()
                    }
                
                profile_stats[profile]['keystrokes'].append(keystroke)
                profile_stats[profile]['sessions'].add(session.get('session_id'))
        
        # Calculate stats per profile
        analysis = {}
        for profile, data in profile_stats.items():
            keystrokes = data['keystrokes']
            
            if len(keystrokes) < 10:
                continue
            
            intervals = [k['interval'] for k in keystrokes if k['interval'] > 0]
            
            if not intervals:
                continue
            
            cpm = len(keystrokes) / (sum(intervals) / 60) if sum(intervals) > 0 else 0
            consistency = (1 - (statistics.stdev(intervals) / statistics.mean(intervals))) * 100 if len(intervals) > 1 else 0
            flow_score = cpm * (consistency / 100)
            
            analysis[profile] = {
                'sessions_count': len(data['sessions']),
                'total_keystrokes': len(keystrokes),
                'avg_cpm': round(cpm, 2),
                'avg_consistency': round(consistency, 2),
                'flow_score': round(flow_score, 2)
            }
        
        # Rank profiles by flow score
        ranked = sorted(analysis.items(), key=lambda x: x[1]['flow_score'], reverse=True)
        
        print(f"🏆 FREQUENCY RANKINGS (by Flow Score):\n")
        for i, (profile, stats) in enumerate(ranked, 1):
            print(f"  {i}. {profile.upper()}")
            print(f"     Sessions: {stats['sessions_count']}")
            print(f"     Keystrokes: {stats['total_keystrokes']}")
            print(f"     CPM: {stats['avg_cpm']}")
            print(f"     Consistency: {stats['avg_consistency']}%")
            print(f"     Flow Score: {stats['flow_score']}")
            print()
        
        if ranked:
            best_profile = ranked[0][0]
            best_score = ranked[0][1]['flow_score']
            print(f"{'='*60}")
            print(f"✨ OPTIMAL FREQUENCY: {best_profile.upper()}")
            print(f"   Flow Score: {best_score}")
            print(f"{'='*60}\n")
            
            analysis['_ranking'] = {
                'best_overall': best_profile,
                'best_flow_score': best_score
            }
        
        return analysis


def main():
    """Command-line interface"""
    import sys
    
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════╗
║         RESONANCE TRACKER - Command Line Tool              ║
╚════════════════════════════════════════════════════════════╝

USAGE:
    python resonance_tracker.py start    # Start monitoring
    python resonance_tracker.py stop     # Stop and save session
    python resonance_tracker.py analyze  # Analyze all sessions

WORKFLOW:
    1. Start monitoring before working
    2. Work normally (frequencies tracked automatically)
    3. Stop when done to save session
    4. After multiple sessions, run analyze
    
OUTPUT:
    Sessions saved to: %USERPROFILE%\\Documents\\ResonanceSync\\keystroke_logs\\
    
DISCOVER:
    Which frequency produces your optimal flow state!
        """)
        sys.exit(0)
    
    tracker = ResonanceTracker()
    
    if not tracker.available:
        print("\n❌ Cannot start - pynput not installed")
        print("   Install: pip install pynput")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        tracker.start_monitoring()
        try:
            # Show live stats every 10 seconds
            while tracker.monitoring:
                time.sleep(10)
                stats = tracker.get_live_stats()
                if stats:
                    print(f"  [LIVE] CPM: {stats['cpm']} | Flow: {stats['flow_score']} | Profile: {stats['profile']}")
        except KeyboardInterrupt:
            print("\n\n⏹ Stopping...")
            tracker.stop_monitoring()
    
    elif command == 'stop':
        tracker.stop_monitoring()
    
    elif command == 'analyze':
        tracker.analyze_all_sessions()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use: start, stop, or analyze")


if __name__ == "__main__":
    main()
