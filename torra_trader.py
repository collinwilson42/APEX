"""
TORRA TRADER v3.1 — Multi-Agent Decision Framework + Dual Screenshot
=====================================================================
Seed 19: The Rewired Engine + Seed 22: Multi-Agent Debate + Seed 24: Dual Screenshot

The trader is a PIPE, not a brain. It does:
  screenshot(per-timeframe region) → Agent Debate (4 specialized analysts + bull/bear + risk gate)
  → ATH injection → DB write → read verdict → execute

Falls back to legacy single-shot Claude if agents are disabled or fail.

The DATABASE is the brain (instance_database.save_sentiment()):
  - Applies profile weights → composite
  - Blends cross-timeframe consensus
  - Checks thresholds → BUY / SELL / HOLD
  - Freezes weights_snapshot for reproducibility

The trader has ZERO internal scoring state. Every tick writes to DB,
reads the verdict back, and either executes or holds.

Seed 24: Each timeframe gets its OWN mss screenshot region from trading_config:
  trading_config.screenshot_regions.15m = {left, top, width, height}
  trading_config.screenshot_regions.1h  = {left, top, width, height}

Schedule (matches sentiment_engine):
  15m analysis: X:01, X:16, X:31, X:46  (1 min after 15m candle close)
  1h  analysis: X:02                     (2 min after 1h candle close)

Usage:
  python torra_trader.py --instance-id xauj26_sim_abc12345
  python torra_trader.py --instance-id xauj26_sim_abc12345 --once
"""

import os
import sys
import json
import time
import base64
import signal
import logging
import argparse
import re
from datetime import datetime
from typing import Optional, Dict

# ── Imports ──
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[WARN] anthropic not installed: pip install anthropic")

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    print("[WARN] mss not installed: pip install mss")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scoring_rubric import build_scoring_prompt
from config import SYMBOL_DATABASES
from ath_calculator import calculate_ath_score

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARN] MetaTrader5 not installed - SL/TP price calculation disabled")

try:
    from mt5_live_position_sync import PositionSyncManager
    HAS_POSITION_SYNC = True
except ImportError:
    HAS_POSITION_SYNC = False
    print("[WARN] mt5_live_position_sync not available - position sync disabled")

try:
    from instance_database import get_instance_db
    HAS_INSTANCE_DB = True
except ImportError:
    HAS_INSTANCE_DB = False
    print("[WARN] instance_database not available")

# ── Seed 22: Multi-Agent Framework ──
try:
    from agent_framework import run_debate, build_memory_context
    from agent_config import resolve_agent_config, DEFAULT_AGENT_CONFIG
    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False
    print("[WARN] agent_framework not available — using legacy single-shot scoring")


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

SCHEDULE_15M = (1, 16, 31, 46)
SCHEDULE_1H  = (2,)

DEFAULT_SIGNAL_PATH = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Roaming", "MetaQuotes", "Terminal", "Common", "Files",
    "webhook_signals.txt"
)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# ── Seed 24: Default screenshot regions for 3840×2140 native resolution ──
# These are overridden by trading_config.screenshot_regions if present
DEFAULT_SCREENSHOT_REGIONS = {
    "15m": {"left": 1040, "top": 200, "width": 1840, "height": 520},
    "1h":  {"left": 1040, "top": 710, "width": 1840, "height": 500},
}


# ═══════════════════════════════════════════════════════════════════════════
# SCREENSHOT — Seed 24: Per-timeframe mss capture
# ═══════════════════════════════════════════════════════════════════════════

def capture_screenshot(region=None) -> Optional[str]:
    """
    Capture screen region → base64 PNG via mss.
    
    Args:
        region: tuple (left, top, width, height) in native pixels,
                or None for full primary monitor
    
    Returns:
        Base64-encoded PNG string, or None on failure
    """
    if not HAS_MSS:
        return None
    try:
        with mss.mss() as sct:
            if region:
                monitor = {
                    "left": region[0], "top": region[1],
                    "width": region[2], "height": region[3]
                }
            else:
                monitor = sct.monitors[1]  # Primary monitor
            shot = sct.grab(monitor)
            png = mss.tools.to_png(shot.rgb, shot.size)
            return base64.standard_b64encode(png).decode("utf-8")
    except Exception as e:
        logging.error(f"Screenshot failed: {e}")
        return None


def get_screenshot_region(trading_config: dict, timeframe: str) -> Optional[tuple]:
    """
    Seed 24: Get mss capture region for a specific timeframe from trading_config.
    
    Looks up trading_config.screenshot_regions.<timeframe> → {left, top, width, height}
    Falls back to DEFAULT_SCREENSHOT_REGIONS if not configured.
    
    Returns:
        (left, top, width, height) tuple, or None for fullscreen
    """
    regions = trading_config.get("screenshot_regions", DEFAULT_SCREENSHOT_REGIONS)
    region_cfg = regions.get(timeframe)
    
    if not region_cfg:
        # Fall back to defaults
        region_cfg = DEFAULT_SCREENSHOT_REGIONS.get(timeframe)
    
    if region_cfg and isinstance(region_cfg, dict):
        left = region_cfg.get("left", 0)
        top = region_cfg.get("top", 0)
        width = region_cfg.get("width", 0)
        height = region_cfg.get("height", 0)
        if width > 0 and height > 0:
            return (left, top, width, height)
    
    return None  # Fullscreen fallback


# ═══════════════════════════════════════════════════════════════════════════
# CLAUDE API — Returns 4 visual vectors (PA, KL, MOM, STR)
# ═══════════════════════════════════════════════════════════════════════════

def score_chart(client, image_b64: str, symbol: str, timeframe_label: str,
                model: str = "claude-sonnet-4-20250514") -> Optional[Dict]:
    """Send screenshot to Claude → 4 visual vector scores + composite_bias gut."""
    prompt = build_scoring_prompt(symbol, timeframe_label)

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0.1,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        raw = resp.content[0].text.strip()
        
        # Strip markdown code fences if present
        clean = re.sub(r'^```(?:json)?\s*', '', raw)
        clean = re.sub(r'\s*```\s*$', '', clean)

        # Try to extract JSON even if Claude returned prose around it
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to find JSON object within the response
            match = re.search(r'\{[\s\S]*\}', clean)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # Log what Claude actually said so we can debug
            logging.error(f"JSON parse failed. Claude response (first 300 chars): {raw[:300]}")
            return None

    except json.JSONDecodeError as e:
        logging.error(f"JSON parse failed: {e}")
        return None
    except Exception as e:
        logging.error(f"API call failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# SIGNAL WRITER — Writes JSON to MT5 webhook_signals.txt
# ═══════════════════════════════════════════════════════════════════════════

def write_signal(path: str, action: str, symbol: str,
                 qty: float = 1.0, sl: float = 0, tp: float = 0,
                 comment: str = "") -> bool:
    """
    Write JSON signal to MT5 webhook_signals.txt.
    
    ALIGNMENT with Protection & Detection EA v6.7:
      - EA reads from FILE_COMMON → Terminal/Common/Files/webhook_signals.txt
      - EA parses: action, symbol, qty/lots, sl, tp
      - EA marks file as "PROCESSED" after reading
      - sl/tp must be ABSOLUTE PRICE LEVELS (not points)
    """
    sig = {
        "action": action.upper(),
        "symbol": symbol,
        "qty": round(qty, 2),
        "comment": comment or "TORRA"
    }
    if sl > 0:
        sig["sl"] = round(sl, 5)
    if tp > 0:
        sig["tp"] = round(tp, 5)

    try:
        sig_dir = os.path.dirname(path)
        if sig_dir:
            os.makedirs(sig_dir, exist_ok=True)
        payload = json.dumps(sig)
        with open(path, 'w', encoding='ascii', errors='replace', newline='\n') as f:
            f.write(payload)
        # Verify the write
        file_size = os.path.getsize(path)
        print(f"  [signal] File written: {path} ({file_size} bytes)")
        print(f"  [signal] Payload: {payload}")
        logging.info(f"SIGNAL -> {path}: {payload}")
        return True
    except PermissionError as e:
        logging.error(f"Signal write PERMISSION ERROR: {e}")
        return False
    except Exception as e:
        logging.error(f"Signal write failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _extract(scores: Dict, key: str) -> float:
    """Safely extract numeric score from API response."""
    val = scores.get(key, 0)
    if isinstance(val, dict):
        return float(val.get("score", 0))
    return float(val)


def _extract_note(scores: Dict, key: str) -> str:
    """Safely extract note text from API response."""
    val = scores.get(key, "")
    if isinstance(val, dict):
        return val.get("note", "")
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# CONFIG-FIRST VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

def validate_config(db, instance) -> dict:
    """
    Validate that everything needed to trade is present.
    Returns {'valid': True/False, 'errors': [...], 'profile': Profile|None, 'trading_config': dict|None}
    """
    errors = []

    # Instance must exist
    if not instance:
        return {'valid': False, 'errors': ['Instance not found'], 'profile': None, 'trading_config': None}

    # Profile must be linked
    if not instance.profile_id:
        errors.append('No profile linked to instance — configure in Profile Manager')
        return {'valid': False, 'errors': errors, 'profile': None, 'trading_config': None}

    # Profile must exist
    profile = db.get_profile(instance.profile_id)
    if not profile:
        errors.append(f'Profile {instance.profile_id} not found in database')
        return {'valid': False, 'errors': errors, 'profile': None, 'trading_config': None}

    # Parse trading_config
    tc = None
    if profile.trading_config:
        try:
            tc = json.loads(profile.trading_config) if isinstance(profile.trading_config, str) else profile.trading_config
        except (json.JSONDecodeError, TypeError):
            tc = None

    if not tc:
        errors.append('Profile has no valid trading_config')
        return {'valid': False, 'errors': errors, 'profile': profile, 'trading_config': None}

    # Weights must exist and be reasonable
    sw = tc.get('sentiment_weights', {})
    if not sw:
        errors.append('trading_config missing sentiment_weights')
    else:
        w_sum = sum(float(v) for v in sw.values())
        if abs(w_sum - 1.0) > 0.05:
            errors.append(f'sentiment_weights sum to {w_sum:.3f}, expected ~1.0')

    # Thresholds must exist
    if not tc.get('thresholds'):
        errors.append('trading_config missing thresholds')

    # API client must be creatable
    api_key = (os.getenv("TORRA_API_KEY")
               or os.getenv("ANTHROPIC_API_KEY")
               or os.getenv("GOOGLE_API_KEY")
               or os.getenv("OPENAI_API_KEY"))
    if not api_key:
        errors.append('No API key — configure in Profile Manager and activate from frontend')

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'profile': profile,
        'trading_config': tc
    }


# ═══════════════════════════════════════════════════════════════════════════
# TORRA TRADER — Thin Executor
# ═══════════════════════════════════════════════════════════════════════════

class TorraTrader:
    """
    Config-first thin executor.
    
    Per tick: screenshot(region) → Claude API (4 vectors) → ATH injection → DB write → read verdict → execute.
    The database (save_sentiment) is the scoring brain. This class just pipes data through.
    
    Seed 24: Each timeframe captures its own screen region via mss.
    """

    def __init__(self, instance_id: str, db_path: str = None,
                 signal_path: str = DEFAULT_SIGNAL_PATH):
        self.instance_id = instance_id
        self.signal_path = signal_path
        self._shutdown = False

        # ── Database ──
        db_path = db_path or os.path.join(BASE_DIR, "apex_instances.db")
        self.db = get_instance_db(db_path)

        # ── Load & validate instance + profile ──
        self.instance = self.db.get_instance(instance_id)
        config_check = validate_config(self.db, self.instance)

        if not config_check['valid']:
            for err in config_check['errors']:
                print(f"  ✗ {err}")
            print("\n  Trader cannot start without valid config. Exiting.")
            sys.exit(1)

        self.profile = config_check['profile']
        self.tc = config_check['trading_config']
        self.symbol = self.instance.symbol

        # ── API client ──
        api_key = (os.getenv("TORRA_API_KEY")
                   or os.getenv("ANTHROPIC_API_KEY")
                   or os.getenv("GOOGLE_API_KEY")
                   or os.getenv("OPENAI_API_KEY"))
        self.provider = os.getenv("TORRA_PROVIDER", "anthropic")
        self.model = os.getenv("TORRA_MODEL") or self.profile.sentiment_model or "claude-sonnet-4-20250514"
        self.client = anthropic.Anthropic(api_key=api_key) if api_key and HAS_ANTHROPIC else None

        # ── Rate limiting ──
        self._last_15m_minute = -1
        self._last_1h_minute = -1
        self._last_signal_time = None
        self._signals_this_hour = 0
        self._hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        self._iteration = 0

        # ── Extract display values from trading_config ──
        sw = self.tc.get('sentiment_weights', {})
        tw = self.tc.get('timeframe_weights', {})
        th = self.tc.get('thresholds', {})
        risk = self.tc.get('risk', {})

        # ── MT5 Connection for live price data (SL/TP calculation) ──
        self._mt5_connected = False
        if MT5_AVAILABLE:
            if mt5.initialize():
                self._mt5_connected = True
                print(f"  ✓ MT5 connected for live price data")
            else:
                print(f"  ✗ MT5 not connected — SL/TP will be skipped")

        # ── Position Sync Manager ──
        self._sync_manager = None
        if HAS_POSITION_SYNC and self._mt5_connected:
            try:
                self._sync_manager = PositionSyncManager(self.db, poll_interval=2.0)
                # Resolve MT5 symbol for sync
                lookup = self.symbol.replace('.sim', '').replace('.SIM', '').upper()
                sym_cfg = SYMBOL_DATABASES.get(lookup, {})
                mt5_sym = sym_cfg.get('symbol', self.symbol)
                if self._sync_manager.start_sync(self.instance_id, mt5_sym):
                    print(f"  ✓ Position sync started ({mt5_sym})")
                else:
                    print(f"  ✗ Position sync failed to start")
            except Exception as e:
                print(f"  ✗ Position sync init error: {e}")

        # ── Seed 24: Screenshot regions ──
        ss_regions = self.tc.get('screenshot_regions', DEFAULT_SCREENSHOT_REGIONS)
        r15 = ss_regions.get('15m', DEFAULT_SCREENSHOT_REGIONS['15m'])
        r1h = ss_regions.get('1h', DEFAULT_SCREENSHOT_REGIONS['1h'])

        # ── Agent mode detection (Seed 22) ──
        self._agent_mode = "legacy"
        if HAS_AGENTS:
            agent_cfg = self.tc.get("agents", {})
            if agent_cfg.get("enabled", True):
                self._agent_mode = agent_cfg.get("mode", "budget")

        # ── Startup banner ──
        print("\n" + "=" * 60)
        print("  TORRA TRADER v3.1 — DUAL SCREENSHOT + MULTI-AGENT")
        print(f"  Instance:  {self.instance_id}")
        print(f"  Symbol:    {self.symbol}")
        print(f"  Profile:   {self.profile.name} ({self.profile.id})")
        print(f"  Model:     {self.model}")
        print(f"  Threshold: +/-{th.get('buy', 0.55)}")
        print(f"  Weights:   PA:{sw.get('price_action',0):.2f} KL:{sw.get('key_levels',0):.2f} "
              f"MOM:{sw.get('momentum',0):.2f} ATH:{sw.get('ath',0.10):.2f} STR:{sw.get('structure',0):.2f}")
        print(f"  TF Blend:  15m:{tw.get('15m',0.40):.2f} | 1h:{tw.get('1h',0.60):.2f}")
        print(f"  Lot Size:  {risk.get('base_lots', 1.0)}")
        print(f"  Signal:    {self.signal_path}")
        print(f"  Capture:   mss (per-timeframe regions)")
        print(f"    15m:     left={r15.get('left')}, top={r15.get('top')}, "
              f"{r15.get('width')}x{r15.get('height')}")
        print(f"    1h:      left={r1h.get('left')}, top={r1h.get('top')}, "
              f"{r1h.get('width')}x{r1h.get('height')}")
        # Seed 22: Agent mode
        if self._agent_mode != "legacy":
            acfg = self._get_agent_config() if HAS_AGENTS else {}
            agents_list = acfg.get('active_agents', [])
            print(f"  Agents:    {self._agent_mode.upper()} mode ({len(agents_list)} agents)")
            print(f"             {', '.join(agents_list)}")
        else:
            print(f"  Agents:    LEGACY (single-shot Claude)")
        print("=" * 60)

    # ─── Schedule ─────────────────────────────────────────────────────

    def _is_15m_tick(self) -> bool:
        m = datetime.now().minute
        if m in SCHEDULE_15M and m != self._last_15m_minute:
            self._last_15m_minute = m
            return True
        return False

    def _is_1h_tick(self) -> bool:
        m = datetime.now().minute
        if m in SCHEDULE_1H and m != self._last_1h_minute:
            self._last_1h_minute = m
            return True
        return False

    def _reset_hourly(self):
        now = datetime.now()
        hour = now.replace(minute=0, second=0, microsecond=0)
        if hour > self._hour_start:
            self._hour_start = hour
            self._signals_this_hour = 0

    # ─── Agent Config (Seed 22) ────────────────────────────────────

    def _use_agents(self) -> bool:
        """Check if agent framework should be used for this tick."""
        if not HAS_AGENTS:
            return False
        agent_cfg = self.tc.get("agents", {})
        return agent_cfg.get("enabled", True)

    def _get_agent_config(self) -> dict:
        """Get resolved agent config from profile trading_config."""
        profile_agent_cfg = self.tc.get("agents", {})
        return resolve_agent_config(profile_agent_cfg)

    # ─── Core Pipeline (per tick) ─────────────────────────────────────

    def _tick(self, timeframe: str):
        """
        Full pipeline for one timeframe tick:
          1. Screenshot (per-timeframe region via mss — Seed 24)
          2. Claude API → 4 visual vectors
          3. ATH score (deterministic, from intelligence DB)
          4. save_sentiment() → DB applies weights, blends, decides
          5. Read verdict from DB
          6. Execute if meets_threshold
        """
        self._iteration += 1
        tf_label = "15-minute" if timeframe == "15m" else "1-hour"
        now_iso = datetime.utcnow().isoformat() + "Z"

        # Hot-reload config so UI changes take effect immediately
        self._reload_config()
        _th = self.tc.get('thresholds', {})
        _risk = self.tc.get('risk', {})

        print(f"\n---- {timeframe.upper()} TICK @ {datetime.now().strftime('%H:%M')} "
              f"{'─' * 40}")
        print(f"  Config: BUY>={_th.get('buy', 0.55):+.3f}  SELL<={_th.get('sell', -0.55):+.3f}  "
              f"lots={_risk.get('base_lots', 1.0)}  cd={_risk.get('cooldown_seconds', 300)}s")

        if not self.client:
            logging.error("  No API client -> skipping tick")
            return

        # ── 1. Chart Capture — Seed 24: Per-timeframe mss region ──
        image_b64 = None
        region = get_screenshot_region(self.tc, timeframe)

        if region:
            print(f"  [capture] {timeframe} chart via mss region "
                  f"({region[0]},{region[1]} {region[2]}x{region[3]})")
        else:
            print(f"  [capture] {timeframe} chart via mss (fullscreen — no region configured)")

        image_b64 = capture_screenshot(region)

        if not image_b64:
            logging.error(f"  [capture] mss capture failed -> skipping tick")
            elapsed_ms = 0
            self._save_error_row(timeframe, now_iso, elapsed_ms, "CAPTURE_ERROR")
            return

        size_kb = len(image_b64) // 1024
        print(f"  [capture] Chart captured ({size_kb}KB) via mss {'region' if region else 'fullscreen'}")

        # ── 2. Scoring: Base (Claude visual) + Agent Adjustments (Seed 22) ──
        start = time.time()
        agent_deliberation = None
        source_type = "API"

        # 2a. Always get base visual scores from legacy single-shot
        base_scores = score_chart(self.client, image_b64, self.symbol, tf_label, self.model)
        if not base_scores:
            elapsed_ms = int((time.time() - start) * 1000)
            self._save_error_row(timeframe, now_iso, elapsed_ms, "API_ERROR")
            return

        pa  = _extract(base_scores, "price_action")
        kl  = _extract(base_scores, "key_levels")
        mom = _extract(base_scores, "momentum")
        stru = _extract(base_scores, "structure")
        print(f"  [score] Base -> PA:{pa:+.2f}  KL:{kl:+.2f}  MOM:{mom:+.2f}  STR:{stru:+.2f}")

        # 2b. If agents enabled, run debate and layer adjustments on top
        if HAS_AGENTS and self._use_agents():
            try:
                agent_cfg = self._get_agent_config()
                context = {
                    "symbol": self.symbol,
                    "timeframe_label": tf_label,
                    "screenshot_b64": image_b64,
                    "l1_scores": {
                        "price_action": pa,
                        "key_levels": kl,
                        "momentum": mom,
                        "structure": stru,
                    },
                    "indicator_snapshot": {},
                }
                print(f"  [agents] Debate ({agent_cfg.get('mode', 'budget')} mode)...")
                debate_scores = run_debate(
                    client=self.client,
                    context=context,
                    agent_config=agent_cfg,
                    db=self.db,
                    instance_id=self.instance_id,
                )
                agent_deliberation = debate_scores.pop("agent_deliberation", None)

                adj_pa  = _extract(debate_scores, "price_action")
                adj_kl  = _extract(debate_scores, "key_levels")
                adj_mom = _extract(debate_scores, "momentum")
                adj_str = _extract(debate_scores, "structure")

                pa  = max(-1.0, min(1.0, pa  + adj_pa))
                kl  = max(-1.0, min(1.0, kl  + adj_kl))
                mom = max(-1.0, min(1.0, mom + adj_mom))
                stru = max(-1.0, min(1.0, stru + adj_str))

                source_type = "AGENT_DEBATE"
                print(f"  [agents] Adjustments -> PA:{adj_pa:+.3f}  KL:{adj_kl:+.3f}  MOM:{adj_mom:+.3f}  STR:{adj_str:+.3f}")
                print(f"  [agents] Final blend -> PA:{pa:+.2f}  KL:{kl:+.2f}  MOM:{mom:+.2f}  STR:{stru:+.2f}")
            except Exception as e:
                logging.warning(f"  [agents] Debate failed, keeping base scores: {e}")

        elapsed_ms = int((time.time() - start) * 1000)

        mode_label = f"Agent Debate ({source_type})" if source_type == "AGENT_DEBATE" else "Claude API"
        print(f"  [score] {mode_label} -> 4 vectors ({elapsed_ms}ms)")

        # ── 3. ATH score (deterministic, from intelligence DB) ──
        ath_result = calculate_ath_score(self.symbol)
        ath_score = ath_result.get("score", 0.0)
        print(f"  [ath] ATH score: {ath_score:+.2f} ({ath_result.get('percentile', 50):.0f}th pctl, "
              f"{ath_result.get('zone', '?')})")

        # ── 4. save_sentiment() → DB is the brain ──
        sentiment_data = {
            "profile_id":          self.profile.id,
            "symbol":              self.symbol,
            "timeframe":           timeframe,
            "timestamp":           now_iso,
            "price_action_score":  pa,
            "key_levels_score":    kl,
            "momentum_score":      mom,
            "ath_score":           ath_score,
            "structure_score":     stru,
            "source_model":        self.model,
            "source_type":         source_type,
            "processing_time_ms":  elapsed_ms,
        }

        # Attach agent deliberation if available (Seed 22)
        if agent_deliberation:
            sentiment_data["agent_deliberation"] = json.dumps(
                agent_deliberation, default=str
            ) if isinstance(agent_deliberation, dict) else str(agent_deliberation)

        try:
            reading_id = self.db.save_sentiment(self.instance_id, sentiment_data, self.profile)
        except Exception as e:
            logging.error(f"  [db] Save FAILED: {e} — refusing to trade")
            return

        # ── 5. Read verdict from DB ──
        verdict = self.db.get_latest_sentiment(self.instance_id, timeframe)
        if not verdict:
            logging.error("  [db] Could not read verdict from DB")
            return

        consensus = verdict.get("consensus_score", 0)
        meets = verdict.get("meets_threshold", 0)
        direction = verdict.get("signal_direction", "HOLD")
        composite = verdict.get("composite_score", 0)
        partner = verdict.get("partner_composite")

        print(f"  [db] Verdict: composite={composite:+.3f} | "
              f"partner={partner if partner is not None else 'N/A'} | "
              f"consensus={consensus:+.3f}")

        emoji = {"BUY": ">>", "SELL": "<<", "HOLD": "--"}.get(direction, "--")
        status = "MET" if meets else "NOT MET"
        print(f"  [{emoji}] {direction} | threshold: {status}")

        # ── 6. Execute if meets_threshold ──
        if meets and direction in ("BUY", "SELL"):
            self._execute_signal(direction)
        else:
            print(f"  [hold] No signal — holding")

    def _save_error_row(self, timeframe: str, timestamp: str, elapsed_ms: int, error_type: str):
        """Save a partial sentiment row on API/screenshot failure."""
        try:
            self.db.save_sentiment(self.instance_id, {
                "profile_id":         self.profile.id,
                "symbol":             self.symbol,
                "timeframe":          timeframe,
                "timestamp":          timestamp,
                "price_action_score": 0, "key_levels_score": 0,
                "momentum_score": 0, "ath_score": 0, "structure_score": 0,
                "source_model":       self.model,
                "source_type":        error_type,
                "processing_time_ms": elapsed_ms,
            }, self.profile)
            print(f"  [db] Saved error row ({error_type}) — signal: HOLD")
        except Exception as e:
            logging.error(f"  Error row save also failed: {e}")

    def _reload_config(self):
        """Hot-reload trading config from DB profile (Seed 20C: live config)."""
        try:
            profile = self.db.get_profile(self.profile.id)
            if profile and profile.trading_config:
                tc = json.loads(profile.trading_config) if isinstance(profile.trading_config, str) else profile.trading_config
                if tc and tc.get('thresholds'):
                    self.tc = tc
                    return True
        except Exception as e:
            logging.warning(f"Config reload failed (using cached): {e}")
        return False

    def _execute_signal(self, direction: str):
        """Rate-limit check → write signal to MT5."""
        self._reset_hourly()
        risk = self.tc.get('risk', {})
        max_sigs = risk.get('max_signals_per_hour', 3)
        cooldown = risk.get('cooldown_seconds', 300)

        # Rate limit
        if self._signals_this_hour >= max_sigs:
            print(f"  [limit] Rate limit: {self._signals_this_hour}/{max_sigs} this hour")
            return

        # Cooldown
        if self._last_signal_time:
            elapsed = (datetime.now() - self._last_signal_time).total_seconds()
            if elapsed < cooldown:
                print(f"  [cooldown] {cooldown - elapsed:.0f}s remaining")
                return

        # Resolve MT5 symbol — strip .sim/.SIM suffix for config lookup
        lookup_key = self.symbol.replace('.sim', '').replace('.SIM', '').upper()
        sym_config = SYMBOL_DATABASES.get(lookup_key, {})
        mt5_symbol = sym_config.get("symbol", lookup_key + ".sim")
        lot_size = risk.get('base_lots', 1.0)
        print(f"  [signal] Symbol resolve: instance='{self.symbol}' -> lookup='{lookup_key}' -> mt5='{mt5_symbol}'")

        # ── Calculate SL/TP from current price + risk config ──
        sl_price = 0
        tp_price = 0
        sl_points = risk.get('stop_loss_points', 0)
        tp_points = risk.get('take_profit_points', 0)

        if (sl_points > 0 or tp_points > 0) and self._mt5_connected and MT5_AVAILABLE:
            try:
                tick = mt5.symbol_info_tick(mt5_symbol)
                if tick:
                    # Get point size for this symbol
                    sym_info = mt5.symbol_info(mt5_symbol)
                    point = sym_info.point if sym_info else 0.01

                    if direction == "BUY":
                        entry_price = tick.ask
                        if sl_points > 0:
                            sl_price = entry_price - (sl_points * point)
                        if tp_points > 0:
                            tp_price = entry_price + (tp_points * point)
                    else:  # SELL
                        entry_price = tick.bid
                        if sl_points > 0:
                            sl_price = entry_price + (sl_points * point)
                        if tp_points > 0:
                            tp_price = entry_price - (tp_points * point)

                    print(f"  [sl/tp] Entry~{entry_price:.5f} | SL={sl_price:.5f} ({sl_points}pts) | TP={tp_price:.5f} ({tp_points}pts)")
                else:
                    print(f"  [sl/tp] No tick data for {mt5_symbol} — sending without SL/TP")
            except Exception as e:
                print(f"  [sl/tp] Price fetch failed: {e} — sending without SL/TP")
        elif sl_points > 0 or tp_points > 0:
            print(f"  [sl/tp] MT5 not connected — cannot calculate price levels")

        comment = (f"TORRA|{direction}|{self.instance_id[:20]}|iter{self._iteration}")

        written = write_signal(
            path=self.signal_path,
            action=direction,
            symbol=mt5_symbol,
            qty=lot_size,
            sl=sl_price,
            tp=tp_price,
            comment=comment
        )

        if written:
            self._signals_this_hour += 1
            self._last_signal_time = datetime.now()
            print(f"  [SIGNAL] -> MT5: {direction} {lot_size} {mt5_symbol}")

    # ─── Run Modes ────────────────────────────────────────────────────

    def run_once(self, timeframe: str = "15m"):
        """Single tick for testing."""
        self._tick(timeframe)

    def run_loop(self, run_now=False):
        """Main loop — follows sentiment engine schedule."""
        def handle_shutdown(signum, frame):
            logging.info(f"Received signal {signum}, shutting down...")
            self._shutdown = True

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

        print(f"\n  Schedule:  15m@{SCHEDULE_15M} | 1h@{SCHEDULE_1H}")

        # Seed 18: --run-now does an immediate 15m tick on activation
        if run_now:
            print("  [run-now] Immediate first tick...")
            try:
                self._tick("15m")
            except Exception as e:
                logging.error(f"  Immediate tick failed (non-fatal): {e}")
                print(f"  Immediate tick error: {e} — entering schedule loop")
        else:
            print("  Waiting for next scheduled tick...")
        print()

        try:
            while not self._shutdown:
                did_something = False

                if self._is_15m_tick():
                    try:
                        self._tick("15m")
                    except Exception as e:
                        logging.error(f"  15m TICK FAILED (non-fatal): {e}")
                        print(f"  15m tick error: {e} — trader continues")
                    did_something = True

                if self._is_1h_tick():
                    try:
                        self._tick("1h")
                    except Exception as e:
                        logging.error(f"  1h TICK FAILED (non-fatal): {e}")
                        print(f"  1h tick error: {e} — trader continues")
                    did_something = True

                if not did_something:
                    now = datetime.now()
                    if now.second < 10 and now.minute % 5 == 0:
                        next_15m = min((m for m in SCHEDULE_15M if m > now.minute), default=SCHEDULE_15M[0])
                        print(f"  [heartbeat] {now.strftime('%H:%M')} — waiting (next 15m tick at :{next_15m:02d})")

                time.sleep(10)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            logging.error(f"  FATAL LOOP ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Stop position sync
            if self._sync_manager:
                self._sync_manager.stop_all()
                print("  Position sync stopped")
            # Shutdown MT5
            if self._mt5_connected and MT5_AVAILABLE:
                try:
                    mt5.shutdown()
                except:
                    pass
            print(f"\n{'=' * 60}")
            print(f"  TORRA TRADER STOPPED — {self._iteration} iterations")
            print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    parser = argparse.ArgumentParser(description="TORRA Trader v3.1 — Dual Screenshot + Multi-Agent")
    parser.add_argument("--instance-id", help="Instance ID from instance database")
    parser.add_argument("--symbol", help="Symbol (if --auto-create)")
    parser.add_argument("--auto-create", action="store_true",
                        help="Auto-create instance if --symbol given without --instance-id")
    parser.add_argument("--once", action="store_true", help="Single tick, no loop")
    parser.add_argument("--run-now", action="store_true",
                        help="Run an immediate 15m tick on startup, then follow schedule")
    parser.add_argument("--timeframe", default="15m", choices=["15m", "1h"],
                        help="Timeframe for --once mode")
    parser.add_argument("--signal-path", default=DEFAULT_SIGNAL_PATH)
    parser.add_argument("--db-path", default=None)

    args = parser.parse_args()

    instance_id = args.instance_id

    if not instance_id and args.symbol and args.auto_create:
        db_path = args.db_path or os.path.join(BASE_DIR, "apex_instances.db")
        db = get_instance_db(db_path)
        inst = db.create_instance(args.symbol.upper(), "SIM",
                                  display_name=f"{args.symbol.upper()} TORRA v2")
        instance_id = inst.id
        print(f"Auto-created instance: {instance_id}")

    if not instance_id:
        parser.error("Provide --instance-id or --symbol with --auto-create")

    try:
        trader = TorraTrader(instance_id, db_path=args.db_path,
                             signal_path=args.signal_path)

        if args.once:
            trader.run_once(args.timeframe)
        else:
            trader.run_loop(run_now=args.run_now)
    except SystemExit:
        raise
    except Exception as e:
        logging.error(f"\n{'=' * 60}")
        logging.error(f"  FATAL: Unhandled exception crashed the trader")
        logging.error(f"  {type(e).__name__}: {e}")
        logging.error(f"{'=' * 60}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
