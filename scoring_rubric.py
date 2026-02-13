"""
SCORING RUBRIC - Claude API Sentiment Training Prompts
=====================================================
Seed 17: The First Run

This module contains the structured prompts that "train" Claude to score
each sentiment vector consistently. The key insight:

    Claude doesn't learn between API calls. Every call is stateless.
    So the "training" IS the prompt — the rubric IS the teacher.

We give Claude explicit scoring anchors (what does 0.8 look like vs 0.3?)
so every call produces calibrated, comparable scores.
"""


def build_scoring_prompt(symbol: str, timeframe: str) -> str:
    """
    Build the full scoring prompt for a given symbol and timeframe.
    
    This prompt is the entire "training" — Claude sees this fresh every call.
    The rubric anchors ensure consistent scoring across calls.
    """
    
    return f"""You are a professional futures trader scoring a {timeframe} chart for {symbol}.

Analyze the chart image and score EXACTLY 5 categories. Each score is a float from -1.0 (extremely bearish) to +1.0 (extremely bullish).

Your scores will be fed into a weighted algorithm that places real trades. Be precise. Be calibrated. Do not default to neutral — commit to what the chart is showing you.

═══════════════════════════════════════════════
CATEGORY 1: PRICE ACTION (What is price doing RIGHT NOW?)
═══════════════════════════════════════════════

SCORING ANCHORS:
  +0.8 to +1.0 → Strong bullish engulfing / breakout above resistance / series of large green candles
  +0.4 to +0.7 → Higher lows forming / bullish candles dominating / price above recent swing
  +0.1 to +0.3 → Slightly bullish lean / more green than red / marginal higher highs
  -0.1 to +0.1 → Doji / indecision / spinning tops / no clear direction
  -0.3 to -0.1 → Slightly bearish lean / more red than green / marginal lower lows
  -0.7 to -0.4 → Lower highs forming / bearish candles dominating / price below recent swing
  -1.0 to -0.8 → Strong bearish engulfing / breakdown below support / series of large red candles

═══════════════════════════════════════════════
CATEGORY 2: KEY LEVELS (Where is price relative to structure?)
═══════════════════════════════════════════════

SCORING ANCHORS:
  +0.8 to +1.0 → Bouncing cleanly off major support / holding above breakout level
  +0.4 to +0.7 → Above EMAs / mid-range with room to run / near support with bounce signal
  +0.1 to +0.3 → Slightly above average / near lower Bollinger band (potential bounce)
  -0.1 to +0.1 → Trapped in the middle / equidistant from support and resistance
  -0.3 to -0.1 → Slightly below average / near upper Bollinger band (potential rejection)
  -0.7 to -0.4 → Below EMAs / rejected from resistance / breaking below support
  -1.0 to -0.8 → Rejected hard from major resistance / free-falling through levels

═══════════════════════════════════════════════
CATEGORY 3: MOMENTUM (Is the move accelerating or fading?)
═══════════════════════════════════════════════

SCORING ANCHORS:
  +0.8 to +1.0 → Accelerating bullish: candles getting BIGGER upward / RSI rising toward 70+ / MACD histogram expanding green
  +0.4 to +0.7 → Steady bullish momentum / consistent upward pressure / no divergence
  +0.1 to +0.3 → Mild bullish momentum / candles shrinking but still green / possible deceleration
  -0.1 to +0.1 → Flat / exhaustion / candles tiny / momentum indicators flat-lined
  -0.3 to -0.1 → Mild bearish momentum / candles shrinking but still red / deceleration
  -0.7 to -0.4 → Steady bearish momentum / consistent downward pressure
  -1.0 to -0.8 → Accelerating bearish: candles getting BIGGER downward / RSI falling toward 30- / MACD expanding red

═══════════════════════════════════════════════
CATEGORY 4: ALL TIME HIGH (Where are we in the bigger picture?)
═══════════════════════════════════════════════

NOTE: ATH score is calculated AUTOMATICALLY from historical data (percentile rank).
You do NOT need to score this category — it will be injected by the system.
However, you may OPTIONALLY comment on ATH context in your composite_bias note.

The system calculates:
  Near ATH (top 10%) → +0.6 to +1.0 (bullish conviction / breakout territory)
  Upper range (25-10%) → +0.2 to +0.5 (healthy uptrend)
  Mid range (25-75%) → -0.2 to +0.2 (neutral territory)
  Lower range (75-90%) → -0.5 to -0.2 (weakness / recovery play)
  Far from ATH (bottom 10%) → -1.0 to -0.6 (deep bearish / capitulation zone)

═══════════════════════════════════════════════
CATEGORY 5: STRUCTURE (What regime/pattern is forming?)
═══════════════════════════════════════════════

SCORING ANCHORS:
  +0.8 to +1.0 → Clear uptrend / higher highs + higher lows / bull flag / ascending triangle
  +0.4 to +0.7 → Bullish structure forming / accumulation pattern / breaking above consolidation
  +0.1 to +0.3 → Neutral-to-bullish lean / symmetrical triangle with slight upward bias
  -0.1 to +0.1 → Range-bound / no clear structure / choppy / sideways consolidation
  -0.3 to -0.1 → Neutral-to-bearish lean / symmetrical triangle with slight downward bias
  -0.7 to -0.4 → Bearish structure forming / distribution pattern / breaking below consolidation
  -1.0 to -0.8 → Clear downtrend / lower highs + lower lows / bear flag / descending triangle

═══════════════════════════════════════════════
RESPONSE FORMAT
═══════════════════════════════════════════════

Respond with ONLY valid JSON. No markdown. No backticks. No explanation outside the JSON.

{{
    "price_action": {{
        "score": 0.0,
        "note": "One sentence: what price is doing"
    }},
    "key_levels": {{
        "score": 0.0,
        "note": "One sentence: where price sits relative to levels"
    }},
    "momentum": {{
        "score": 0.0,
        "note": "One sentence: strength/weakness of current move"
    }},
    "structure": {{
        "score": 0.0,
        "note": "One sentence: the regime or pattern"
    }},
    "composite_bias": {{
        "score": 0.0,
        "note": "One sentence: your overall read on this chart (ATH context is auto-injected)"
    }}
}}

CRITICAL RULES:
1. Scores MUST be between -1.0 and +1.0
2. Do NOT default to 0.0 — take a position based on what you see
3. The "composite_bias" is YOUR overall gut read, independent of the category math
4. Be specific in notes — mention visible price levels, patterns, candle shapes
5. If the chart is unclear or you cannot determine a direction, bias toward 0.0 (not a random guess)
6. You only score 4 categories — ATH (All Time High) is calculated automatically by the system"""


def build_dual_timeframe_prompt(symbol: str) -> dict:
    """
    Returns prompts for both timeframes.
    In practice, you'd call the API twice — once per timeframe screenshot.
    Or once if both timeframes are visible on the same screen.
    """
    return {
        "15m": build_scoring_prompt(symbol, "15-minute"),
        "1h": build_scoring_prompt(symbol, "1-hour")
    }


# ═══════════════════════════════════════════════════════════════════════════
# TRAINING EXPLANATION (for documentation / human reference)
# ═══════════════════════════════════════════════════════════════════════════

TRAINING_EXPLANATION = """
HOW CLAUDE "LEARNS" TO SCORE
============================

Claude is stateless between API calls. It doesn't retain memory of previous 
scoring sessions. So the "training" is entirely in the prompt structure.

Three mechanisms make scoring consistent:

1. ANCHORED RUBRICS
   Each score range (e.g., +0.4 to +0.7) has explicit descriptions of what 
   that range LOOKS like on a chart. This prevents drift — Claude can't 
   give a 0.8 to a flat chart because the rubric defines 0.8 as 
   "accelerating bullish candles."

2. STRUCTURED OUTPUT
   By requiring JSON with both a score AND a note, we force Claude to 
   justify its score. The note acts as a self-check — if the note says 
   "price is flat" but the score is 0.7, there's internal inconsistency 
   that the model will self-correct.

3. COMPOSITE INDEPENDENCE
   The composite_bias score is Claude's holistic gut read, separate from 
   the individual categories. This gives us a cross-check — if the weighted 
   math says +0.6 but Claude's gut says -0.2, that's a signal to HOLD.

CALIBRATION OVER TIME
   As you collect scored data, you can:
   - Compare Claude scores vs actual price outcomes
   - Identify which vectors are most predictive
   - Adjust profile weights based on real performance
   - Refine rubric anchors to be even more specific to your instrument
"""
