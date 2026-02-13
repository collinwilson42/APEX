"""
TORRA TRADER v2.0 — Config-First Thin Executor
================================================
Seed 19: The Rewired Engine

The trader is a PIPE, not a brain. It does:
  screenshot → Claude API (4 visual vectors) → ATH injection → DB write → read verdict → execute

The DATABASE is the brain (instance_database.save_sentiment()):
  - Applies profile weights → composite
  - Blends cross-timeframe consensus
  - Checks thresholds → BUY / SELL / HOLD
  - Freezes weights_snapshot for reproducibility

The trader has ZERO internal scoring state. Every tick writes to DB,
reads the verdict back, and either executes or holds.

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
from datetime import datetime
from typing import Optional, Dict

# ── Imports ──
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️  anthropic not installed: pip install anthropic")

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    print("⚠️  mss not installed: pip install mss")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scoring_rubric import build_scoring_prompt
from config import SYMBOL_DATABASES
from ath_calculator import calculate_ath_score

try:
    from instance_database import get_instance_db
    HAS_INSTANCE_DB = True
except ImportError:
    HAS_INSTANCE_DB = False
    print("⚠️  instance_database not available")


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


# ═══════════════════════════════════════════════════════════════════════════
# SCREENSHOT
# ═══════════════════════════════════════════════════════════════════════════

def capture_screenshot(region=None) -> Optional[str]:
    """Capture screen → base64 PNG."""
    if not HAS_MSS:
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
        logging.error(f"Screenshot failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# CLAUDE API — Returns 4 visual vectors (PA, KL, MOM, STR)
# ═══════════════════════════════════════════════════════════════════════════

def score_chart(client, image_b64: str, symbol: str, timeframe_label: str,
                model: str = "claude-sonnet-4-20250514") -> Optional[Dict]:
    """Send screenshot to Claude → 4 visual vector scores + composite_bias gut."""
    import re
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
        clean = re.sub(r'^```json\s*', '', raw)
        clean = re.sub(r'\s*```$', '', clean)
        return json.loads(clean)

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
        with open(path, 'w', encoding='ascii', errors='replace', newline='\n') as f:
            f.write(json.dumps(sig))
        logging.info(f"📝 SIGNAL → {path}: {json.dumps(sig)}")
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
    
    Per tick: screenshot → Claude API (4 vectors) → ATH injection → DB write → read verdict → execute.
    The database (save_sentiment) is the scoring brain. This class just pipes data through.
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

        # ── Startup banner ──
        print("\n" + "═" * 60)
        print("  🔷 TORRA TRADER v2.0 — CONFIG-FIRST EXECUTOR")
        print(f"  Instance:  {self.instance_id}")
        print(f"  Symbol:    {self.symbol}")
        print(f"  Profile:   {self.profile.name} ({self.profile.id})")
        print(f"  Model:     {self.model}")
        print(f"  Threshold: ±{th.get('buy', 0.55)}")
        print(f"  Weights:   PA:{sw.get('price_action',0):.2f} KL:{sw.get('key_levels',0):.2f} "
              f"MOM:{sw.get('momentum',0):.2f} ATH:{sw.get('ath',0.10):.2f} STR:{sw.get('structure',0):.2f}")
        print(f"  TF Blend:  15m:{tw.get('15m',0.40):.2f} | 1h:{tw.get('1h',0.60):.2f}")
        print(f"  Lot Size:  {risk.get('base_lots', 1.0)}")
        print(f"  Signal:    {self.signal_path}")
        print("═" * 60)

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

    # ─── Core Pipeline (per tick) ─────────────────────────────────────

    def _tick(self, timeframe: str):
        """
        Full pipeline for one timeframe tick:
          1. Screenshot
          2. Claude API → 4 visual vectors
          3. ATH score (deterministic, from intelligence DB)
          4. save_sentiment() → DB applies weights, blends, decides
          5. Read verdict from DB
          6. Execute if meets_threshold
        """
        self._iteration += 1
        tf_label = "15-minute" if timeframe == "15m" else "1-hour"
        now_iso = datetime.utcnow().isoformat() + "Z"

        print(f"\n──── {timeframe.upper()} TICK @ {datetime.now().strftime('%H:%M')} "
              f"{'─' * 40}")

        if not self.client:
            logging.error("  No API client → skipping tick")
            return

        # ── 1. Screenshot ──
        image_b64 = capture_screenshot()
        if not image_b64:
            logging.error("  📸 Screenshot failed → skipping tick")
            return
        print(f"  📸 Screenshot captured ({len(image_b64) // 1024}KB)")

        # ── 2. Claude API → 4 visual vectors ──
        start = time.time()
        scores = score_chart(self.client, image_b64, self.symbol, tf_label, self.model)
        elapsed_ms = int((time.time() - start) * 1000)

        if not scores:
            # API failure → save partial row, signal HOLD
            self._save_error_row(timeframe, now_iso, elapsed_ms, "API_ERROR")
            return

        pa  = _extract(scores, "price_action")
        kl  = _extract(scores, "key_levels")
        mom = _extract(scores, "momentum")
        stru = _extract(scores, "structure")

        print(f"  🤖 Claude API → 4 visual vectors ({elapsed_ms}ms)")
        print(f"     PA:{pa:+.2f}  KL:{kl:+.2f}  MOM:{mom:+.2f}  STR:{stru:+.2f}")

        # ── 3. ATH score (deterministic, from intelligence DB) ──
        ath_result = calculate_ath_score(self.symbol)
        ath_score = ath_result.get("score", 0.0)
        print(f"  📊 ATH score: {ath_score:+.2f} ({ath_result.get('percentile', 50):.0f}th pctl, "
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
            "source_type":         "API",
            "processing_time_ms":  elapsed_ms,
        }

        try:
            reading_id = self.db.save_sentiment(self.instance_id, sentiment_data, self.profile)
        except Exception as e:
            logging.error(f"  💾 DB save FAILED: {e} — refusing to trade")
            return

        # ── 5. Read verdict from DB ──
        verdict = self.db.get_latest_sentiment(self.instance_id, timeframe)
        if not verdict:
            logging.error("  📖 Could not read verdict from DB")
            return

        consensus = verdict.get("consensus_score", 0)
        meets = verdict.get("meets_threshold", 0)
        direction = verdict.get("signal_direction", "HOLD")
        composite = verdict.get("composite_score", 0)
        partner = verdict.get("partner_composite")

        print(f"  💾 DB verdict: composite={composite:+.3f} | "
              f"partner={partner if partner is not None else 'N/A'} | "
              f"consensus={consensus:+.3f}")

        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(direction, "⚪")
        status = "MET ✓" if meets else "NOT MET ·"
        print(f"  {emoji} {direction} | threshold: {status}")

        # ── 6. Execute if meets_threshold ──
        if meets and direction in ("BUY", "SELL"):
            self._execute_signal(direction)
        else:
            print(f"  ⏸️  No signal — holding")

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
            print(f"  💾 Saved error row ({error_type}) — signal: HOLD")
        except Exception as e:
            logging.error(f"  Error row save also failed: {e}")

    def _execute_signal(self, direction: str):
        """Rate-limit check → write signal to MT5."""
        self._reset_hourly()
        risk = self.tc.get('risk', {})
        max_sigs = risk.get('max_signals_per_hour', 3)
        cooldown = risk.get('cooldown_seconds', 300)

        # Rate limit
        if self._signals_this_hour >= max_sigs:
            print(f"  🚫 Rate limit: {self._signals_this_hour}/{max_sigs} this hour")
            return

        # Cooldown
        if self._last_signal_time:
            elapsed = (datetime.now() - self._last_signal_time).total_seconds()
            if elapsed < cooldown:
                print(f"  ⏳ Cooldown: {cooldown - elapsed:.0f}s remaining")
                return

        # Resolve MT5 symbol
        sym_config = SYMBOL_DATABASES.get(self.symbol, {})
        mt5_symbol = sym_config.get("symbol", self.symbol + ".sim")
        lot_size = risk.get('base_lots', 1.0)

        comment = (f"TORRA|{direction}|{self.instance_id[:20]}|iter{self._iteration}")

        written = write_signal(
            path=self.signal_path,
            action=direction,
            symbol=mt5_symbol,
            qty=lot_size,
            sl=0,   # EA handles SL/TP — we don't have live price
            tp=0,
            comment=comment
        )

        if written:
            self._signals_this_hour += 1
            self._last_signal_time = datetime.now()
            print(f"  ✅ SIGNAL → MT5: {direction} {lot_size} {mt5_symbol}")

    # ─── Run Modes ────────────────────────────────────────────────────

    def run_once(self, timeframe: str = "15m"):
        """Single tick for testing."""
        self._tick(timeframe)

    def run_loop(self):
        """Main loop — follows sentiment engine schedule."""
        def handle_shutdown(signum, frame):
            logging.info(f"Received signal {signum}, shutting down...")
            self._shutdown = True

        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

        print(f"\n  Schedule:  15m@{SCHEDULE_15M} | 1h@{SCHEDULE_1H}")
        print("  Waiting for next scheduled tick...\n")

        try:
            while not self._shutdown:
                did_something = False

                if self._is_15m_tick():
                    self._tick("15m")
                    did_something = True

                if self._is_1h_tick():
                    self._tick("1h")
                    did_something = True

                if not did_something:
                    now = datetime.now()
                    if now.second < 10 and now.minute % 5 == 0:
                        next_15m = min((m for m in SCHEDULE_15M if m > now.minute), default=SCHEDULE_15M[0])
                        print(f"  💓 {now.strftime('%H:%M')} — waiting (next 15m tick at :{next_15m:02d})")

                time.sleep(10)

        except KeyboardInterrupt:
            pass
        finally:
            print(f"\n{'═'*60}")
            print(f"  TORRA TRADER STOPPED — {self._iteration} iterations")
            print(f"{'═'*60}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    parser = argparse.ArgumentParser(description="TORRA Trader v2.0 — Config-First Executor")
    parser.add_argument("--instance-id", help="Instance ID from instance database")
    parser.add_argument("--symbol", help="Symbol (if --auto-create)")
    parser.add_argument("--auto-create", action="store_true",
                        help="Auto-create instance if --symbol given without --instance-id")
    parser.add_argument("--once", action="store_true", help="Single tick, no loop")
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
        print(f"✓ Auto-created instance: {instance_id}")

    if not instance_id:
        parser.error("Provide --instance-id or --symbol with --auto-create")

    trader = TorraTrader(instance_id, db_path=args.db_path,
                         signal_path=args.signal_path)

    if args.once:
        trader.run_once(args.timeframe)
    else:
        trader.run_loop()


if __name__ == "__main__":
    main()
