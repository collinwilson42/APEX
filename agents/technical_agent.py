"""
TECHNICAL AGENT — Chart Pattern & Trend Structure Specialist
=============================================================
Seed 22: Multi-Agent Decision Framework

Reads the chart screenshot + Layer 1 scores + indicator snapshot.
Focuses on: Price Action (PA) and Structure (STR) vectors.
Provides adjustments where visual patterns add info indicators miss.

This is the workhorse agent — active in every mode (budget through full).
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

TECHNICAL_PROMPT_TEMPLATE = """You are a Technical Analyst on a professional futures trading desk reviewing a {timeframe} chart for {symbol}.

YOUR ROLE: You specialize in chart patterns, candle formations, and visual trend structure. You see things that raw indicator numbers miss — formations, confluences, visual anomalies.

═══════════════════════════════════════════════
DETERMINISTIC SCORES (already calculated by our quant engine)
═══════════════════════════════════════════════
  Price Action: {pa_score:+.4f} — {pa_note}
  Key Levels:   {kl_score:+.4f} — {kl_note}
  Momentum:     {mom_score:+.4f} — {mom_note}
  Structure:    {str_score:+.4f} — {str_note}

═══════════════════════════════════════════════
INDICATOR SNAPSHOT
═══════════════════════════════════════════════
{indicator_text}

═══════════════════════════════════════════════
MARKET MEMORY (from our database)
═══════════════════════════════════════════════
{memory_text}

═══════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════
Look at the chart screenshot. Provide ADJUSTMENTS to the existing scores based on what you SEE that the indicators miss.

Focus on YOUR specialties:
  - **Price Action:** Candle patterns (engulfing, hammer, doji at key levels), gap analysis, wick rejection, body-to-wick ratios in context
  - **Structure:** Trend regime (HH/HL vs LH/LL), chart patterns (H&S, flags, wedges, triangles, channels), breakout/breakdown setups

You may also comment on Key Levels and Momentum if you see something visually significant, but your PRIMARY vectors are PA and STR.

ADJUSTMENT RULES:
  1. Each adjustment is -0.3 to +0.3 (you are fine-tuning, not rescoring)
  2. 0.0 means the quant engine captured it well — no visual override needed
  3. Cite specific visual evidence for any non-zero adjustment
  4. If market is closed or chart is static, use 0.0

Respond with ONLY valid JSON:
{{
    "agent_id": "technical",
    "adjustments": {{
        "price_action": 0.0,
        "key_levels": 0.0,
        "momentum": 0.0,
        "structure": 0.0
    }},
    "confidence": "medium",
    "reasoning": "One paragraph: what you see on the chart that modifies the quant scores",
    "flags": []
}}

CONFIDENCE: "high" = clear pattern visible, "medium" = suggestive but ambiguous, "low" = noisy/unclear chart
FLAGS: Optional list of alerts like "possible_head_and_shoulders", "gap_unfilled", "volume_divergence", "trend_exhaustion"
"""


def build_prompt(context: dict) -> str:
    """Build the technical agent prompt from shared context."""
    l1 = context.get("l1_scores", {})
    snap = context.get("indicator_snapshot", {})
    memory = context.get("memory_context", {})

    # Format indicator text
    indicator_lines = []
    if snap:
        indicator_lines = [
            f"Price:       close={snap.get('last_close', 'N/A')}, open={snap.get('last_open', 'N/A')}",
            f"EMA:         Short={_sf(snap.get('ema_short'))}, Med={_sf(snap.get('ema_medium'))}, Dist={_sf(snap.get('ema_distance'), signed=True)}%",
            f"Supertrend:  {snap.get('supertrend', 'N/A')}   SAR: {snap.get('sar_trend', 'N/A')}",
            f"RSI(14):     {_sf(snap.get('rsi_14'))}",
            f"MACD:        Line={_sf(snap.get('macd_line'), signed=True)} Signal={_sf(snap.get('macd_signal'), signed=True)} Hist={_sf(snap.get('macd_histogram'), signed=True)}",
            f"BB:          %B={_sf(snap.get('bb_pct'))} Width={_sf(snap.get('bb_width'))}",
            f"Stoch:       K={_sf(snap.get('stoch_k'))} D={_sf(snap.get('stoch_d'))}",
            f"ADX:         {_sf(snap.get('adx'))}",
            f"Ichimoku:    TK={_sf(snap.get('ichimoku_tenkan'))} KJ={_sf(snap.get('ichimoku_kijun'))}",
            f"Fib Zone:    {snap.get('fib_zone', 'N/A')}  Golden={'YES' if snap.get('in_golden_zone') else 'NO'}",
        ]
    indicator_text = "\n".join(indicator_lines) if indicator_lines else "(No indicator data available)"

    # Format memory text
    memory_lines = []
    if memory:
        if memory.get("current_markov_state"):
            memory_lines.append(f"Current State:  {memory['current_markov_state']} (held for {memory.get('state_duration', '?')} ticks)")
        if memory.get("sentiment_trend"):
            trend = memory["sentiment_trend"]
            direction = memory.get("trend_direction", "flat")
            memory_lines.append(f"Consensus Trend: {' → '.join(f'{v:+.3f}' for v in trend[-5:])} ({direction})")
        if memory.get("open_positions"):
            for pos in memory["open_positions"][:3]:
                memory_lines.append(f"Open Position:  {pos.get('direction')} | PnL: {pos.get('pnl', 0):+.2f} | Age: {pos.get('age_ticks', '?')} ticks")
        if memory.get("recent_signals"):
            memory_lines.append(f"Recent Signals: {' → '.join(memory['recent_signals'][-5:])}")
    memory_text = "\n".join(memory_lines) if memory_lines else "(No memory context available)"

    # L1 scores
    pa = l1.get("price_action", {})
    kl = l1.get("key_levels", {})
    mom = l1.get("momentum", {})
    stru = l1.get("structure", {})

    return TECHNICAL_PROMPT_TEMPLATE.format(
        timeframe=context.get("timeframe_label", "15-minute"),
        symbol=context.get("symbol", "UNKNOWN"),
        pa_score=_score_val(pa), pa_note=_score_note(pa),
        kl_score=_score_val(kl), kl_note=_score_note(kl),
        mom_score=_score_val(mom), mom_note=_score_note(mom),
        str_score=_score_val(stru), str_note=_score_note(stru),
        indicator_text=indicator_text,
        memory_text=memory_text,
    )


def run_technical_agent(client, context: dict, model: str) -> dict:
    """
    Execute the technical agent.
    
    Args:
        client: Anthropic API client
        context: Shared context (l1_scores, indicator_snapshot, screenshot_b64, memory_context)
        model: Model string to use
        
    Returns:
        Agent output dict with adjustments, reasoning, confidence, flags
    """
    prompt = build_prompt(context)
    image_b64 = context.get("screenshot_b64")

    content = []
    if image_b64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": image_b64}
        })
    content.append({"type": "text", "text": prompt})

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=800,
            temperature=0.15,
            messages=[{"role": "user", "content": content}]
        )
        raw = resp.content[0].text.strip()
        clean = re.sub(r'^```json\s*', '', raw)
        clean = re.sub(r'\s*```$', '', clean)
        result = json.loads(clean)

        # Ensure structure
        result.setdefault("agent_id", "technical")
        result.setdefault("adjustments", {})
        result.setdefault("confidence", "medium")
        result.setdefault("reasoning", "")
        result.setdefault("flags", [])

        # Clamp adjustments
        for key in ("price_action", "key_levels", "momentum", "structure"):
            val = float(result["adjustments"].get(key, 0))
            result["adjustments"][key] = max(-0.3, min(0.3, val))

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"[TechnicalAgent] JSON parse failed: {e}")
        return _empty_result("JSON parse error")
    except Exception as e:
        logger.error(f"[TechnicalAgent] API call failed: {e}")
        return _empty_result(str(e))


def _empty_result(error_msg: str = "") -> dict:
    return {
        "agent_id": "technical",
        "adjustments": {"price_action": 0.0, "key_levels": 0.0, "momentum": 0.0, "structure": 0.0},
        "confidence": "low",
        "reasoning": f"Agent failed: {error_msg}" if error_msg else "Agent did not respond",
        "flags": ["agent_error"],
    }


def _sf(val, signed=False) -> str:
    """Safe format a numeric value."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        return f"{v:+.3f}" if signed else f"{v:.3f}"
    except (ValueError, TypeError):
        return str(val)


def _score_val(score_dict) -> float:
    if isinstance(score_dict, dict):
        return float(score_dict.get("score", 0))
    return float(score_dict or 0)


def _score_note(score_dict) -> str:
    if isinstance(score_dict, dict):
        return score_dict.get("note", "")
    return ""
