"""
V11 Streamlit App - Vision & Indicator Integration
===================================================
Provides:
- Chart screenshot capture
- Claude Vision API analysis
- Indicator calculations and storage
- M15 context provider
- Real-time position state visualization
"""

import streamlit as st
import sqlite3
import json
import base64
import io
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import anthropic
from PIL import Image
import mss
import mss.tools

# Configure page
st.set_page_config(
    page_title="MT5 Meta Agent V11 - Vision",
    page_icon="&#128065;",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DB_PATH = os.environ.get('DB_PATH', 'mt5_intelligence.db')
FLASK_API_URL = os.environ.get('FLASK_API_URL', 'http://localhost:5000/api/v11')

# =============================================================================
# AUTO-INITIALIZE DATABASE (ALWAYS RUNS)
# =============================================================================

def ensure_database_exists():
    """Initialize database tables - handles old schemas and creates missing tables"""
    print(f"[V11] Ensuring database exists: {DB_PATH}")
    
    # Check if old schema exists and needs full reset
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Check for old schema by looking at evaluation_settings structure
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evaluation_settings'")
            if cursor.fetchone():
                cursor.execute("PRAGMA table_info(evaluation_settings)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'setting_name' not in columns:
                    print("[V11] Old schema detected - recreating database...")
                    conn.close()
                    os.remove(DB_PATH)
                    print("[V11] Old database removed")
            conn.close()
        except Exception as e:
            print(f"[V11] Schema check failed: {e}")
            # Try to remove corrupt db
            try:
                os.remove(DB_PATH)
                print("[V11] Removed corrupt database")
            except:
                pass
    
    # Now create/update tables
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Core tables - CREATE IF NOT EXISTS handles idempotency
    cursor.executescript("""
        -- Position State (MT5 Import)
        CREATE TABLE IF NOT EXISTS position_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL DEFAULT 'XAUG26.sim',
            timeframe TEXT NOT NULL DEFAULT 'M1',
            position_size REAL DEFAULT 0.0,
            pnl REAL DEFAULT 0.0,
            price REAL NOT NULL,
            sl1 REAL, sl2 REAL, sl3 REAL, sl4 REAL, sl5 REAL,
            tp1 REAL, tp2 REAL, tp3 REAL, tp4 REAL, tp5 REAL,
            source_tag TEXT DEFAULT 'mt5_collector',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Streamlit Outputs
        CREATE TABLE IF NOT EXISTS streamlit_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_state_id INTEGER,
            indicator_group TEXT NOT NULL,
            indicator_values TEXT,
            visual_snapshot TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- AI Analysis Results
        CREATE TABLE IF NOT EXISTS ai_analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id TEXT UNIQUE,
            position_state_id INTEGER,
            analysis_type TEXT NOT NULL,
            analysis_result TEXT,
            confidence REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Evaluation Settings
        CREATE TABLE IF NOT EXISTS evaluation_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_name TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Trade Cycles
        CREATE TABLE IF NOT EXISTS trade_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id TEXT UNIQUE,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL DEFAULT 'XAUG26.sim',
            timeframe TEXT NOT NULL DEFAULT 'M1',
            position_state_id INTEGER,
            complex_run_id TEXT,
            master_decision_123 INTEGER,
            webhook_written INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- API Configs
        CREATE TABLE IF NOT EXISTS api_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            sees_position_size INTEGER DEFAULT 0,
            sees_sl_levels INTEGER DEFAULT 1,
            sees_tp_levels INTEGER DEFAULT 1,
            sees_pnl INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- API Profiles
        CREATE TABLE IF NOT EXISTS api_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            skillfile_id TEXT,
            prompt_id TEXT,
            api_id TEXT DEFAULT '[API_CLAUDE_01]',
            config_id TEXT,
            weight REAL DEFAULT 1.0,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- API Complexes
        CREATE TABLE IF NOT EXISTS api_complexes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complex_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            profile_1_id TEXT,
            profile_2_id TEXT,
            profile_3_id TEXT,
            profile_4_id TEXT,
            consensus_threshold REAL DEFAULT 0.75,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- API Masters
        CREATE TABLE IF NOT EXISTS api_masters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            vision_enabled INTEGER DEFAULT 1,
            override_enabled INTEGER DEFAULT 1,
            sees_position_size INTEGER DEFAULT 0,
            sees_pnl INTEGER DEFAULT 0,
            can_submit_final_sl INTEGER DEFAULT 1,
            can_submit_final_tp INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- API Complex Runs
        CREATE TABLE IF NOT EXISTS api_complex_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            complex_id TEXT NOT NULL,
            position_state_id INTEGER,
            m15_position_state_id INTEGER,
            api_1_decision INTEGER,
            api_2_decision INTEGER,
            api_3_decision INTEGER,
            api_4_decision INTEGER,
            sell_count INTEGER DEFAULT 0,
            hold_count INTEGER DEFAULT 0,
            buy_count INTEGER DEFAULT 0,
            consensus_pct REAL,
            consensus_decision INTEGER,
            master_decision INTEGER,
            master_override_used INTEGER DEFAULT 0,
            final_decision INTEGER,
            final_sl REAL,
            final_tp REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- ID Generation Log
        CREATE TABLE IF NOT EXISTS id_generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_id TEXT UNIQUE NOT NULL,
            id_type TEXT NOT NULL,
            source_components TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert sample position state if empty
        INSERT OR IGNORE INTO position_state (id, timestamp, symbol, timeframe, position_size, pnl, price, sl1, tp1)
        VALUES (1, datetime('now'), 'XAUG26.sim', 'M1', 0.0, 0.0, 2650.00, 2640.00, 2670.00);
        
        -- Insert M15 sample too
        INSERT OR IGNORE INTO position_state (id, timestamp, symbol, timeframe, position_size, pnl, price, sl1, tp1)
        VALUES (2, datetime('now'), 'XAUG26.sim', 'M15', 0.0, 0.0, 2650.00, 2635.00, 2680.00);
        
        -- Default settings
        INSERT OR IGNORE INTO evaluation_settings (setting_name, setting_value, description)
        VALUES 
            ('lot_size_control_factor', '1.0', 'V3 fixed lot size'),
            ('consensus_threshold', '0.75', '75% agreement required'),
            ('default_symbol', 'XAUG26.sim', 'Default symbol'),
            ('vision_enabled', '1', 'Enable vision analysis');
        
        -- Default configs
        INSERT OR IGNORE INTO api_configs (config_id, name, description)
        VALUES 
            ('[CONFIG_001]', 'Standard', 'Default config'),
            ('[CONFIG_002]', 'Conservative', 'Risk-averse');
        
        -- Default masters
        INSERT OR IGNORE INTO api_masters (master_id, name, vision_enabled, override_enabled)
        VALUES 
            ('[MASTER_001]', 'Primary Master', 1, 1),
            ('[MASTER_002]', 'Secondary Master', 1, 1);
        
        -- Default complex
        INSERT OR IGNORE INTO api_complexes (complex_id, name, consensus_threshold)
        VALUES ('[COMPLEX_ALPHA_001]', 'Alpha Complex', 0.75);
    """)
    
    conn.commit()
    conn.close()
    print("[V11] Database tables ready!")

# Run IMMEDIATELY on import
ensure_database_exists()

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0A2540 0%, #1a3a5c 100%);
    }
    .css-1d391kg {
        background-color: rgba(10, 37, 64, 0.9);
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(187, 152, 71, 0.3);
        border-radius: 8px;
        padding: 15px;
    }
    .decision-sell { color: #F87171; font-weight: bold; }
    .decision-hold { color: #8A9BB0; font-weight: bold; }
    .decision-buy { color: #4ADE80; font-weight: bold; }
    h1, h2, h3 { color: #BB9847 !important; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_latest_position_state(symbol: str = 'XAUG26.sim', timeframe: str = 'M1') -> Optional[Dict]:
    """Get latest position state from database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM position_state 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (symbol, timeframe))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_m15_context(symbol: str = 'XAUG26.sim') -> Optional[Dict]:
    """Get latest M15 position state for higher timeframe context"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM position_state 
        WHERE symbol = ? AND timeframe = 'M15'
        ORDER BY timestamp DESC LIMIT 1
    """, (symbol,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def insert_streamlit_output(
    position_state_id: int,
    indicator_group: str,
    indicator_values: str,
    visual_snapshot: Optional[str] = None
) -> int:
    """Insert Streamlit output to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO streamlit_outputs (
            position_state_id, indicator_group, indicator_values, visual_snapshot
        ) VALUES (?, ?, ?, ?)
    """, (position_state_id, indicator_group, indicator_values, visual_snapshot))
    
    output_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return output_id


def insert_ai_analysis(
    analysis_id: str,
    position_state_id: int,
    analysis_type: str,
    analysis_result: str,
    confidence: float
) -> int:
    """Insert AI analysis result to database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO ai_analysis_results (
            analysis_id, position_state_id, analysis_type, analysis_result, 
            confidence, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (analysis_id, position_state_id, analysis_type, analysis_result, 
          confidence, datetime.utcnow().isoformat()))
    
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return result_id


# =============================================================================
# SCREENSHOT CAPTURE
# =============================================================================

def capture_screen_region(
    left: int = 0, 
    top: int = 0, 
    width: int = 1920, 
    height: int = 1080,
    monitor: int = 1
) -> Image.Image:
    """Capture a region of the screen"""
    with mss.mss() as sct:
        # Get monitor info
        if monitor <= len(sct.monitors):
            mon = sct.monitors[monitor]
        else:
            mon = sct.monitors[1]
        
        # Define capture region
        region = {
            "left": mon["left"] + left,
            "top": mon["top"] + top,
            "width": width,
            "height": height
        }
        
        # Capture
        screenshot = sct.grab(region)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        return img


def image_to_base64(img: Image.Image, format: str = 'PNG') -> str:
    """Convert PIL Image to base64 string"""
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def capture_chart_screenshot(
    monitor: int = 1,
    region: Optional[Dict[str, int]] = None
) -> Tuple[Image.Image, str]:
    """
    Capture chart screenshot from specified monitor/region.
    Returns PIL Image and base64 string.
    """
    if region:
        img = capture_screen_region(
            left=region.get('left', 0),
            top=region.get('top', 0),
            width=region.get('width', 1920),
            height=region.get('height', 1080),
            monitor=monitor
        )
    else:
        # Default: full monitor capture
        with mss.mss() as sct:
            mon = sct.monitors[monitor] if monitor <= len(sct.monitors) else sct.monitors[1]
            screenshot = sct.grab(mon)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
    
    base64_str = image_to_base64(img)
    
    return img, base64_str


# =============================================================================
# CLAUDE VISION API
# =============================================================================

def analyze_chart_with_vision(
    image_base64: str,
    position_state: Optional[Dict] = None,
    m15_context: Optional[Dict] = None,
    custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze chart screenshot using Claude Vision API.
    
    Returns:
        {
            'decision': 1/2/3,
            'analysis': str,
            'confidence': float,
            'key_levels': {...},
            'raw_response': str
        }
    """
    client = anthropic.Anthropic()
    
    # Build system prompt
    system_prompt = """You are an expert technical analyst for gold futures trading (XAUG26.sim).
Analyze the provided chart screenshot and give a trading decision.

Your response MUST be in this exact JSON format:
{
    "decision": <1, 2, or 3>,
    "decision_label": "<SELL, HOLD, or BUY>",
    "confidence": <0.0 to 1.0>,
    "analysis": "<brief analysis in 2-3 sentences>",
    "trend": "<BEARISH, NEUTRAL, or BULLISH>",
    "key_resistance": <price level or null>,
    "key_support": <price level or null>,
    "suggested_sl": <price level or null>,
    "suggested_tp": <price level or null>
}

Decision mapping:
- 1 = SELL (bearish setup, short opportunity)
- 2 = HOLD (no clear setup, wait)
- 3 = BUY (bullish setup, long opportunity)

Focus on:
- Price action patterns
- Support/resistance levels
- Trend direction
- Volume if visible
- Any visible indicators"""

    # Build user message
    content = []
    
    # Add image
    content.append({
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": image_base64
        }
    })
    
    # Build text context
    text_parts = ["Analyze this chart and provide your trading decision."]
    
    if position_state:
        text_parts.append(f"\nCurrent M1 Context:")
        text_parts.append(f"- Price: {position_state.get('price', 'N/A')}")
        text_parts.append(f"- Position Size: {position_state.get('position_size', 0)}")
        text_parts.append(f"- P&L: {position_state.get('pnl', 0)}")
    
    if m15_context:
        text_parts.append(f"\nHigher Timeframe (M15) Context:")
        text_parts.append(f"- M15 Price: {m15_context.get('price', 'N/A')}")
        text_parts.append(f"- M15 SL1: {m15_context.get('sl1', 'N/A')}")
        text_parts.append(f"- M15 TP1: {m15_context.get('tp1', 'N/A')}")
    
    if custom_prompt:
        text_parts.append(f"\nAdditional instructions: {custom_prompt}")
    
    content.append({
        "type": "text",
        "text": "\n".join(text_parts)
    })
    
    # Call Claude Vision
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": content}
            ]
        )
        
        raw_response = response.content[0].text
        
        # Parse JSON response
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw_response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"decision": 2, "analysis": raw_response, "confidence": 0.5}
        except json.JSONDecodeError:
            result = {"decision": 2, "analysis": raw_response, "confidence": 0.5}
        
        result['raw_response'] = raw_response
        return result
        
    except Exception as e:
        return {
            "decision": 2,
            "analysis": f"Vision API error: {str(e)}",
            "confidence": 0.0,
            "error": str(e),
            "raw_response": str(e)
        }


# =============================================================================
# INDICATOR CALCULATIONS
# =============================================================================

def calculate_indicators(position_state: Dict) -> Dict[str, Any]:
    """
    Calculate technical indicators from position state.
    Returns indicator groups for storage.
    """
    indicators = {
        "price_levels": {
            "current_price": position_state.get('price'),
            "sl_levels": [
                position_state.get(f'sl{i}') for i in range(1, 6)
                if position_state.get(f'sl{i}')
            ],
            "tp_levels": [
                position_state.get(f'tp{i}') for i in range(1, 6)
                if position_state.get(f'tp{i}')
            ]
        },
        "position_info": {
            "size": position_state.get('position_size', 0),
            "pnl": position_state.get('pnl', 0),
            "direction": "LONG" if position_state.get('position_size', 0) > 0 
                        else "SHORT" if position_state.get('position_size', 0) < 0 
                        else "FLAT"
        },
        "risk_metrics": {
            "risk_to_sl1": None,
            "reward_to_tp1": None,
            "risk_reward_ratio": None
        }
    }
    
    # Calculate risk metrics
    price = position_state.get('price')
    sl1 = position_state.get('sl1')
    tp1 = position_state.get('tp1')
    
    if price and sl1:
        indicators["risk_metrics"]["risk_to_sl1"] = abs(price - sl1)
    if price and tp1:
        indicators["risk_metrics"]["reward_to_tp1"] = abs(tp1 - price)
    if indicators["risk_metrics"]["risk_to_sl1"] and indicators["risk_metrics"]["reward_to_tp1"]:
        risk = indicators["risk_metrics"]["risk_to_sl1"]
        if risk > 0:
            indicators["risk_metrics"]["risk_reward_ratio"] = round(
                indicators["risk_metrics"]["reward_to_tp1"] / risk, 2
            )
    
    return indicators


# =============================================================================
# STREAMLIT UI
# =============================================================================

def main():
    st.title("MT5 Meta Agent V11 - Vision System")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")
        
        symbol = st.text_input("Symbol", value="XAUG26.sim")
        timeframe = st.selectbox("Timeframe", ["M1", "M15"], index=0)
        
        st.subheader("Screenshot Settings")
        monitor = st.number_input("Monitor", min_value=1, max_value=4, value=1)
        
        use_region = st.checkbox("Custom Region")
        if use_region:
            col1, col2 = st.columns(2)
            with col1:
                region_left = st.number_input("Left", value=0)
                region_top = st.number_input("Top", value=0)
            with col2:
                region_width = st.number_input("Width", value=1920)
                region_height = st.number_input("Height", value=1080)
            region = {
                "left": region_left, "top": region_top,
                "width": region_width, "height": region_height
            }
        else:
            region = None
        
        st.subheader("Vision API")
        enable_vision = st.checkbox("Enable Vision Analysis", value=True)
        custom_prompt = st.text_area("Custom Prompt (optional)", height=100)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Position State")
        
        # Fetch latest position state
        position_state = get_latest_position_state(symbol, timeframe)
        
        if position_state:
            # Display metrics
            metric_cols = st.columns(4)
            with metric_cols[0]:
                st.metric("Price", f"{position_state.get('price', 0):.2f}")
            with metric_cols[1]:
                st.metric("Position", f"{position_state.get('position_size', 0):.2f}")
            with metric_cols[2]:
                pnl = position_state.get('pnl', 0)
                st.metric("P&L", f"${pnl:.2f}", delta=pnl)
            with metric_cols[3]:
                st.metric("Timestamp", position_state.get('timestamp', 'N/A')[-8:])
            
            # SL/TP levels
            st.subheader("SL/TP Levels")
            sl_cols = st.columns(5)
            tp_cols = st.columns(5)
            
            for i in range(5):
                with sl_cols[i]:
                    sl_val = position_state.get(f'sl{i+1}')
                    st.metric(f"SL{i+1}", f"{sl_val:.2f}" if sl_val else "-")
                with tp_cols[i]:
                    tp_val = position_state.get(f'tp{i+1}')
                    st.metric(f"TP{i+1}", f"{tp_val:.2f}" if tp_val else "-")
            
            # M15 context
            m15_context = get_m15_context(symbol)
            if m15_context:
                st.subheader("M15 Context")
                m15_cols = st.columns(3)
                with m15_cols[0]:
                    st.metric("M15 Price", f"{m15_context.get('price', 0):.2f}")
                with m15_cols[1]:
                    st.metric("M15 SL1", f"{m15_context.get('sl1', 0):.2f}" if m15_context.get('sl1') else "-")
                with m15_cols[2]:
                    st.metric("M15 TP1", f"{m15_context.get('tp1', 0):.2f}" if m15_context.get('tp1') else "-")
        else:
            st.warning("No position state found. Ensure MT5 collector is running.")
            position_state = {}
            m15_context = None
    
    with col2:
        st.header("Vision Analysis")
        
        # Screenshot capture button
        if st.button("Capture & Analyze", type="primary"):
            with st.spinner("Capturing screenshot..."):
                try:
                    img, img_base64 = capture_chart_screenshot(monitor, region)
                    st.image(img, caption="Captured Chart", use_column_width=True)
                    
                    # Store in session state
                    st.session_state['last_screenshot'] = img
                    st.session_state['last_screenshot_base64'] = img_base64
                    
                except Exception as e:
                    st.error(f"Screenshot failed: {e}")
                    img_base64 = None
            
            if enable_vision and img_base64:
                with st.spinner("Analyzing with Claude Vision..."):
                    result = analyze_chart_with_vision(
                        img_base64,
                        position_state,
                        m15_context,
                        custom_prompt if custom_prompt else None
                    )
                    
                    st.session_state['last_analysis'] = result
                    
                    # Display result
                    decision = result.get('decision', 2)
                    decision_label = {1: 'SELL', 2: 'HOLD', 3: 'BUY'}.get(decision, 'HOLD')
                    decision_color = {1: 'red', 2: 'gray', 3: 'green'}.get(decision, 'gray')
                    
                    st.markdown(f"### Decision: <span style='color:{decision_color}'>{decision_label}</span>", 
                               unsafe_allow_html=True)
                    
                    st.metric("Confidence", f"{result.get('confidence', 0):.0%}")
                    st.write("**Analysis:**", result.get('analysis', 'N/A'))
                    
                    if result.get('suggested_sl'):
                        st.metric("Suggested SL", f"{result.get('suggested_sl'):.2f}")
                    if result.get('suggested_tp'):
                        st.metric("Suggested TP", f"{result.get('suggested_tp'):.2f}")
                    
                    # Store to database
                    if position_state.get('id'):
                        from id_gen_api import IDGenerator
                        id_gen = IDGenerator.get_instance(DB_PATH)
                        analysis_id = id_gen.generate_analysis_id('V')
                        
                        insert_ai_analysis(
                            analysis_id=analysis_id,
                            position_state_id=position_state['id'],
                            analysis_type='VISION',
                            analysis_result=json.dumps(result),
                            confidence=result.get('confidence', 0)
                        )
                        st.success(f"Analysis stored: {analysis_id}")
        
        # Show last analysis if exists
        if 'last_analysis' in st.session_state and not st.button("Clear"):
            st.subheader("Last Analysis")
            result = st.session_state['last_analysis']
            with st.expander("Raw Response"):
                st.code(result.get('raw_response', ''))
    
    # Indicator section
    st.header("Indicators")
    
    if position_state:
        indicators = calculate_indicators(position_state)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Price Levels")
            st.json(indicators["price_levels"])
        
        with col2:
            st.subheader("Position Info")
            st.json(indicators["position_info"])
        
        with col3:
            st.subheader("Risk Metrics")
            st.json(indicators["risk_metrics"])
        
        # Save indicators button
        if st.button("Save Indicators to DB"):
            if position_state.get('id'):
                output_id = insert_streamlit_output(
                    position_state_id=position_state['id'],
                    indicator_group='FULL',
                    indicator_values=json.dumps(indicators)
                )
                st.success(f"Indicators saved! Output ID: {output_id}")
    
    # API Complex trigger
    st.header("API Complex")
    
    col1, col2 = st.columns(2)
    
    with col1:
        complex_id = st.text_input("Complex ID", value="[COMPLEX_ALPHA_001]")
        master_id = st.text_input("Master ID", value="[MASTER_001]")
    
    with col2:
        include_vision = st.checkbox("Include Vision Data", value=True)
        
        if st.button("Run API Complex", type="primary"):
            with st.spinner("Running API complex..."):
                try:
                    payload = {
                        "complex_id": complex_id,
                        "master_id": master_id,
                        "symbol": symbol,
                        "timeframe": timeframe
                    }
                    
                    if include_vision and 'last_screenshot_base64' in st.session_state:
                        payload['vision_data'] = st.session_state['last_screenshot_base64']
                    
                    response = requests.post(
                        f"{FLASK_API_URL}/run_complex",
                        json=payload,
                        timeout=60
                    )
                    
                    if response.ok:
                        result = response.json()['data']
                        
                        st.success(f"Complex run complete! Run ID: {result['run_id']}")
                        
                        # Display decisions
                        st.subheader("API Decisions")
                        decision_cols = st.columns(4)
                        for i, api_dec in enumerate(result['api_decisions']):
                            with decision_cols[i]:
                                dec_val = api_dec['decision']
                                dec_label = {1: 'SELL', 2: 'HOLD', 3: 'BUY'}.get(dec_val, '?')
                                dec_color = {1: '#F87171', 2: '#8A9BB0', 3: '#4ADE80'}.get(dec_val, 'gray')
                                st.markdown(f"<h2 style='color:{dec_color};text-align:center'>{dec_val}</h2>", 
                                           unsafe_allow_html=True)
                                st.caption(api_dec['profile_id'][-12:])
                        
                        # Consensus
                        st.subheader("Consensus")
                        cons = result['consensus']
                        st.write(f"SELL: {cons['sell_count']} | HOLD: {cons['hold_count']} | BUY: {cons['buy_count']}")
                        st.metric("Consensus %", f"{cons['consensus_pct']:.0%}")
                        
                        # Final decision
                        final = result['final_decision']
                        final_label = {1: 'SELL', 2: 'HOLD', 3: 'BUY'}.get(final, '?')
                        final_color = {1: '#F87171', 2: '#8A9BB0', 3: '#4ADE80'}.get(final, 'gray')
                        st.markdown(f"### Final: <span style='color:{final_color}'>{final_label}</span>", 
                                   unsafe_allow_html=True)
                        
                        if result['webhook_written']:
                            st.success("Webhook signal written!")
                    else:
                        st.error(f"API error: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
    
    # Footer
    st.markdown("---")
    st.caption("MT5 Meta Agent V11 | Vision System | ID-Driven Architecture")


if __name__ == "__main__":
    main()