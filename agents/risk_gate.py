"""
RISK GATE — Final Signal Gatekeeper
=====================================
Seed 22: Multi-Agent Decision Framework

The Risk Manager sees EVERYTHING: analyst reports, bull thesis, bear thesis,
L1 scores, memory context, open positions. It produces a MULTIPLIER (0.0 to 1.0)
for each vector that can attenuate or fully veto the signal.

Key difference from other agents: the Risk Gate does NOT produce adjustments.
It produces MULTIPLIERS. A multiplier of 0.0 = full veto on that vector.
A multiplier of 1.0 = full pass-through. 0.5 = cut the adjustment in half.

This is the safety net that prevents the system from trading into danger.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

RISK_GATE_PROMPT_TEMPLATE = """You are the Risk Manager on a professional futures trading desk. You are the FINAL GATE before a trade signal is generated for {symbol} on the {timeframe} timeframe.

You have full visibility into everything: analyst reports, the bull thesis, the bear thesis, our quant scores, and our position memory. Your job is to protect capital.

═══════════════════════════════════════════════
DETERMINISTIC BASE SCORES
═══════════════════════════════════════════════
  Price Action: {pa_score:+.4f}
  Key Levels:   {kl_score:+.4f}
  Momentum:     {mom_score:+.4f}
  Structure:    {str_score:+.4f}

═══════════════════════════════════════════════
DEBATE ADJUSTMENTS (after bull/bear synthesis)
═══════════════════════════════════════════════
  Price Action: {debate_pa:+.4f}
  Key Levels:   {debate_kl:+.4f}
  Momentum:     {debate_mom:+.4f}
  Structure:    {debate_str:+.4f}

═══════════════════════════════════════════════
BULL THESIS (confidence: {bull_confidence})
═══════════════════════════════════════════════
{bull_reasoning}

═══════════════════════════════════════════════
BEAR THESIS (confidence: {bear_confidence})
═══════════════════════════════════════════════
{bear_reasoning}

═══════════════════════════════════════════════
ANALYST FLAGS
═══════════════════════════════════════════════
{all_flags_text}

═══════════════════════════════════════════════
MARKET MEMORY
═══════════════════════════════════════════════
{memory_text}

═══════════════════════════════════════════════
YOUR TASK: PROTECT CAPITAL
═══════════════════════════════════════════════
For each vector, assign a MULTIPLIER from 0.0 to 1.0:
  - 1.0 = "This adjustment is safe, let it through"
  - 0.7 = "I have minor concerns, reduce the impact"
  - 0.3 = "Significant risk here, heavily attenuate"
  - 0.0 = "VETO — do not allow this adjustment to influence the trade"

WHEN TO ATTENUATE:
  - Bull and bear are both low confidence → uncertainty, reduce
  - Multiple danger flags from analysts → reduce
  - We already have open positions in this direction → reduce (overexposure)
  - Market is choppy/range-bound and adjustments suggest a directional trade → reduce
  - It's a Friday afternoon or session overlap with low liquidity → reduce
  - Sentiment trend is reversing against the proposed direction → reduce

WHEN TO VETO (0.0):
  - Analyst flags include "trend_exhaustion" AND bear confidence is high
  - Multiple positions already open AND new signal adds to same direction
  - Three or more danger flags from different analysts

Respond with ONLY valid JSON:
{{
    "agent_id": "risk_gate",
    "multipliers": {{
        "price_action": 1.0,
        "key_levels": 1.0,
        "momentum": 1.0,
        "structure": 1.0
    }},
    "overall_risk_level": "medium",
    "reasoning": "1-2 sentences explaining your risk assessment and any attenuation/veto rationale",
    "flags": [],
    "veto": false
}}

OVERALL_RISK_LEVEL: "low" (safe to trade), "medium" (caution), "high" (strongly attenuate), "extreme" (consider full veto)
VETO: true = recommend NOT trading at all regardless of scores (sets all multipliers to 0)
FLAGS: "overexposed", "uncertainty", "exhaustion_risk", "liquidity_concern", "conflicting_signals", "full_veto"
"""


def build_prompt(context: dict, debate_adjustments: dict,
                 bull_result: dict, bear_result: dict,
                 all_flags: list) -> str:
    """Build the risk gate prompt."""
    l1 = context.get("l1_scores", {})
    memory = context.get("memory_context", {})

    pa = l1.get("price_action", {})
    kl = l1.get("key_levels", {})
    mom = l1.get("momentum", {})
    stru = l1.get("structure", {})

    # Format memory
    memory_lines = []
    if memory:
        if memory.get("current_markov_state"):
            memory_lines.append(f"State: {memory['current_markov_state']} (held {memory.get('state_duration', '?')} ticks)")
        if memory.get("sentiment_trend"):
            trend = memory["sentiment_trend"]
            direction = memory.get("trend_direction", "flat")
            memory_lines.append(f"Consensus Trend: {' → '.join(f'{v:+.3f}' for v in trend[-5:])} ({direction})")
        if memory.get("open_positions"):
            for pos in memory["open_positions"][:3]:
                memory_lines.append(f"Open: {pos.get('direction')} PnL={pos.get('pnl', 0):+.2f} age={pos.get('age_ticks', '?')} ticks")
        elif memory.get("open_positions") is not None:
            memory_lines.append("No open positions")
        if memory.get("recent_signals"):
            memory_lines.append(f"Recent Signals: {' → '.join(memory['recent_signals'][-5:])}")
        if memory.get("session"):
            memory_lines.append(f"Session: {memory['session']}")
        if memory.get("day_of_week"):
            memory_lines.append(f"Day: {memory['day_of_week']}")
    memory_text = "\n".join(memory_lines) if memory_lines else "(No memory context)"

    # Format flags
    flags_text = "\n".join(f"  ⚠️  {f}" for f in all_flags) if all_flags else "  (No flags raised)"

    return RISK_GATE_PROMPT_TEMPLATE.format(
        symbol=context.get("symbol", "UNKNOWN"),
        timeframe=context.get("timeframe_label", "15-minute"),
        pa_score=_score_val(pa), kl_score=_score_val(kl),
        mom_score=_score_val(mom), str_score=_score_val(stru),
        debate_pa=debate_adjustments.get("price_action", 0),
        debate_kl=debate_adjustments.get("key_levels", 0),
        debate_mom=debate_adjustments.get("momentum", 0),
        debate_str=debate_adjustments.get("structure", 0),
        bull_confidence=bull_result.get("confidence", "unknown"),
        bull_reasoning=bull_result.get("reasoning", "No bull thesis provided"),
        bear_confidence=bear_result.get("confidence", "unknown"),
        bear_reasoning=bear_result.get("reasoning", "No bear thesis provided"),
        all_flags_text=flags_text,
        memory_text=memory_text,
    )


def run_risk_gate(client, context: dict, model: str,
                  debate_adjustments: dict = None,
                  bull_result: dict = None,
                  bear_result: dict = None,
                  all_flags: list = None) -> dict:
    """
    Execute the risk gate.

    Args:
        client: Anthropic API client
        context: Shared context dict
        model: Model string
        debate_adjustments: Dict of vector adjustments from debate synthesis
        bull_result: Bull researcher output
        bear_result: Bear researcher output
        all_flags: Consolidated list of flags from all agents

    Returns:
        Risk gate output with multipliers
    """
    debate_adjustments = debate_adjustments or {"price_action": 0, "key_levels": 0, "momentum": 0, "structure": 0}
    bull_result = bull_result or {"confidence": "unknown", "reasoning": "Not available"}
    bear_result = bear_result or {"confidence": "unknown", "reasoning": "Not available"}
    all_flags = all_flags or []

    prompt = build_prompt(context, debate_adjustments, bull_result, bear_result, all_flags)

    # Risk gate does NOT get the screenshot — it works from reports only
    # This is intentional: the risk manager assesses risk from data, not visuals
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = resp.content[0].text.strip()
        clean = re.sub(r'^```json\s*', '', raw)
        clean = re.sub(r'\s*```$', '', clean)
        result = json.loads(clean)

        result.setdefault("agent_id", "risk_gate")
        result.setdefault("multipliers", {})
        result.setdefault("overall_risk_level", "medium")
        result.setdefault("reasoning", "")
        result.setdefault("flags", [])
        result.setdefault("veto", False)

        # Full veto override
        if result.get("veto", False):
            result["multipliers"] = {
                "price_action": 0.0, "key_levels": 0.0,
                "momentum": 0.0, "structure": 0.0
            }
            if "full_veto" not in result["flags"]:
                result["flags"].append("full_veto")

        # Clamp multipliers to [0.0, 1.0]
        for key in ("price_action", "key_levels", "momentum", "structure"):
            val = float(result["multipliers"].get(key, 1.0))
            result["multipliers"][key] = max(0.0, min(1.0, val))

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"[RiskGate] JSON parse failed: {e}")
        return _empty_result("JSON parse error")
    except Exception as e:
        logger.error(f"[RiskGate] API call failed: {e}")
        return _empty_result(str(e))


def _empty_result(error_msg: str = "") -> dict:
    """On failure, pass everything through (fail-open for the risk gate)."""
    return {
        "agent_id": "risk_gate",
        "multipliers": {"price_action": 1.0, "key_levels": 1.0, "momentum": 1.0, "structure": 1.0},
        "overall_risk_level": "unknown",
        "reasoning": f"Risk gate failed ({error_msg}), defaulting to pass-through",
        "flags": ["gate_error"],
        "veto": False,
    }


def _score_val(score_dict) -> float:
    if isinstance(score_dict, dict):
        return float(score_dict.get("score", 0))
    return float(score_dict or 0)
