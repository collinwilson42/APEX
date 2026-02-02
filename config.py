"""
ENGINE CONFIGURATION - CENTRAL SOURCE OF TRUTH
==============================================
All symbol and system configuration for MT5 Meta Agent V11.3

Other files should import from here:
    from config import SYMBOL_DATABASES, DEFAULT_SYMBOL, ACTIVE_SYMBOL
"""

import os

# Get the directory where this config file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# SYMBOL DATABASE CONFIGURATION (SINGLE SOURCE OF TRUTH)
# ============================================================================
# Update these when contracts roll over to new months
# Contract codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, 
#                 N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec

SYMBOL_DATABASES = {
    'XAUJ26': {
        'id': 'XAUJ26',
        'name': 'Gold Futures',
        'symbol': 'XAUJ26.sim',
        'db_path': os.path.join(BASE_DIR, 'XAUJ26_intelligence.db'),
    },
    'USOILH26': {
        'id': 'USOILH26',
        'name': 'Crude Oil Futures',
        'symbol': 'USOILH26.sim',
        'db_path': os.path.join(BASE_DIR, 'USOILH26_intelligence.db'),
    },
    'US500H26': {
        'id': 'US500H26',
        'name': 'S&P 500 Futures',
        'symbol': 'US500H26.sim',
        'db_path': os.path.join(BASE_DIR, 'US500H26_intelligence.db'),
    },
    'US100H26': {
        'id': 'US100H26',
        'name': 'Nasdaq 100 Futures',
        'symbol': 'US100H26.sim',
        'db_path': os.path.join(BASE_DIR, 'US100H26_intelligence.db'),
    },
    'US30H26': {
        'id': 'US30H26',
        'name': 'Dow Jones Futures',
        'symbol': 'US30H26.sim',
        'db_path': os.path.join(BASE_DIR, 'US30H26_intelligence.db'),
    },
    'BTCF26': {
        'id': 'BTCF26',
        'name': 'Bitcoin Futures',
        'symbol': 'BTCF26.sim',
        'db_path': os.path.join(BASE_DIR, 'BTCF26_intelligence.db'),
    }
}

# Default symbol (used when no symbol specified)
DEFAULT_SYMBOL = 'XAUJ26'

# Currently active symbol for trading
ACTIVE_SYMBOL = DEFAULT_SYMBOL

# Legacy single-symbol reference (for backward compatibility)
SYMBOL = SYMBOL_DATABASES[DEFAULT_SYMBOL]['symbol']
DB_PATH = SYMBOL_DATABASES[DEFAULT_SYMBOL]['db_path']

# ============================================================================
# COLLECTOR SETTINGS
# ============================================================================

COLLECTOR_ENABLED = True
COLLECTOR_TIMEFRAMES = ['15m', '1h']  # Migration: Abandoned 1m for 1h (Seed 13)
COLLECTOR_INTERVAL_SEC = 30  # How often to check for new bars

# ============================================================================
# TRADING CONFIGURATION
# ============================================================================

# Risk / Reward Level (0-100)
# 0 = 100% Conservative (only sell/close)
# 50 = Neutral (balanced)
# 100 = 100% Aggressive (maximum buying)
RISK_REWARD_LEVEL = 50

# Base lot size for position sizing
BASE_LOT_SIZE = 1.0
MAX_TOTAL_POSITION = 10.0  # Maximum total position size (lots)

# ============================================================================
# API MANAGEMENT SETTINGS
# ============================================================================

# API SL Management (True = Claude manages SL, False = manual/off)
API_SL_MANAGEMENT = True

# API TP Management (True = Claude manages TP, False = manual/off)
API_TP_MANAGEMENT = True

# ============================================================================
# EXECUTION GATE CONFIGURATION
# ============================================================================

NUM_GATES = 10
BASE_INTERVAL_SEC = 340
PEAK_ZONE_DURATION_SEC = 0

# ============================================================================
# API DECISION ENGINE SETTINGS
# ============================================================================

# ENABLE/DISABLE API (Set to False for testing without API calls)
API_ENABLED = True

# How often to query Claude API (seconds)
API_QUERY_INTERVAL_SEC = 60

# Full analysis interval (with screenshot)
API_FULL_ANALYSIS_INTERVAL_SEC = 900  # 15 minutes

# Lightweight update interval (data only)
API_LIGHTWEIGHT_UPDATE_INTERVAL_SEC = 60  # 1 minute

# Screenshot settings
SCREENSHOT_PATH = "latest_screenshot.png"
SCREENSHOT_FOLDER = r"C:\Users\cwils\OneDrive\Desktop\Adaptive MT5 Meta Agent\V11\screenshots"

# API Key - Use environment variable for security
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# ============================================================================
# WEBHOOK SETTINGS
# ============================================================================

WEBHOOK_FILE_PATH = "webhook_signals.txt"

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

VERBOSE_LOGGING = True
SHOW_COUNTDOWN = True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_symbol_config(symbol_id: str) -> dict:
    """Get configuration for a specific symbol"""
    return SYMBOL_DATABASES.get(symbol_id.upper())


def get_symbol_db_path(symbol_id: str) -> str:
    """Get database path for a symbol"""
    config = get_symbol_config(symbol_id)
    return config['db_path'] if config else None


def get_all_symbol_ids() -> list:
    """Get list of all symbol IDs"""
    return list(SYMBOL_DATABASES.keys())


def get_available_symbols() -> list:
    """Get list of symbols with existing databases"""
    return [
        sym_id for sym_id, config in SYMBOL_DATABASES.items()
        if os.path.exists(config['db_path'])
    ]


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration settings"""
    errors = []
    warnings = []
    
    # Risk level validation
    if not 0 <= RISK_REWARD_LEVEL <= 100:
        errors.append(f"RISK_REWARD_LEVEL must be 0-100, got {RISK_REWARD_LEVEL}")
    
    # Lot size validation
    if BASE_LOT_SIZE < 1.0:
        warnings.append(f"BASE_LOT_SIZE is {BASE_LOT_SIZE}, but gold futures require minimum 1.0")
    
    if MAX_TOTAL_POSITION < BASE_LOT_SIZE:
        errors.append(f"MAX_TOTAL_POSITION ({MAX_TOTAL_POSITION}) must be >= BASE_LOT_SIZE ({BASE_LOT_SIZE})")
    
    # API key check
    if ANTHROPIC_API_KEY is None:
        warnings.append("ANTHROPIC_API_KEY not set - API decisions will be disabled")
    
    # Check symbol databases
    for sym_id, config in SYMBOL_DATABASES.items():
        if not os.path.exists(config['db_path']):
            warnings.append(f"Database not found: {config['db_path']} ({sym_id})")
    
    return errors, warnings


def print_config():
    """Print current configuration"""
    print("=" * 70)
    print("ENGINE CONFIGURATION")
    print("=" * 70)
    
    print(f"\n[SYMBOLS]")
    print(f"  Default Symbol: {DEFAULT_SYMBOL}")
    print(f"  Active Symbol: {ACTIVE_SYMBOL}")
    print(f"\n  Configured Symbols:")
    for sym_id, config in SYMBOL_DATABASES.items():
        exists = "✓" if os.path.exists(config['db_path']) else "✗"
        print(f"    {exists} {sym_id}: {config['symbol']} -> {config['db_path']}")
    
    print(f"\n[TRADING]")
    print(f"  Risk/Reward Level: {RISK_REWARD_LEVEL}")
    
    if RISK_REWARD_LEVEL >= 80:
        risk_desc = "AGGRESSIVE"
    elif RISK_REWARD_LEVEL >= 60:
        risk_desc = "MODERATE-HIGH"
    elif RISK_REWARD_LEVEL >= 40:
        risk_desc = "BALANCED"
    elif RISK_REWARD_LEVEL >= 20:
        risk_desc = "CONSERVATIVE"
    else:
        risk_desc = "VERY CONSERVATIVE"
    
    print(f"  Risk Mode: {risk_desc}")
    print(f"  Base Lot Size: {BASE_LOT_SIZE}")
    print(f"  Max Position: {MAX_TOTAL_POSITION} lots")
    
    print(f"\n[COLLECTOR]")
    print(f"  Enabled: {COLLECTOR_ENABLED}")
    print(f"  Timeframes: {', '.join(COLLECTOR_TIMEFRAMES)}")
    print(f"  Interval: {COLLECTOR_INTERVAL_SEC}s")
    
    print(f"\n[API]")
    print(f"  Enabled: {API_ENABLED}")
    print(f"  SL Management: {'✓' if API_SL_MANAGEMENT else '✗'}")
    print(f"  TP Management: {'✓' if API_TP_MANAGEMENT else '✗'}")
    
    print("=" * 70)
    
    # Validate
    errors, warnings = validate_config()
    
    if errors:
        print("\n✗ ERRORS:")
        for err in errors:
            print(f"  - {err}")
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for warn in warnings:
            print(f"  - {warn}")
    
    if not errors and not warnings:
        print("\n✓ Configuration validated successfully")
    
    print("=" * 70)
    
    return len(errors) == 0


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print_config()
