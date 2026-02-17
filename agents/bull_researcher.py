"""
BULL RESEARCHER — Argues the Bullish Case
==========================================
Seed 22: Multi-Agent Decision Framework

Receives ALL analyst reports, then constructs the strongest possible
bullish argument. Cites specific evidence from analysts.

The Bull and Bear researchers are the core of TradingAgents' edge —
their debate reduces false signals by forcing both sides to justify.
"""

import json
import re
import logging

logger = logging.getLogger(__name__)

BULL_PROMPT_TEMPLATE = """You are the Bull Researcher on a professional futures trading desk. Your job is to argue the BULLISH case for {symbol} on the {timeframe} timeframe.

You have received reports from our analyst team. Your task: build the STRONGEST possible bullish argument from the evidence. Even if the data leans bearish, find whatever bullish signals exist and present them compellingly.

═══════════════════════════════════════════════
ANALYST REPORTS
═══════════════════════════════════════════════
{analyst_reports_text}

═══════════════════════════════════════════════
DETERMINISTIC BASE SCORES
═══════════════════════════════════════════════
  Price Action: {pa_score:+.4f}
  Key Levels:   {kl_score:+.4f}
  Momentum:     {mom_score:+.4f}
  Structure:    {str_score:+.4f}

═══════════════════════════════════════════════
MARKET MEMORY
═══════════════════════════════════════════════
{memory_text}

═══════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════
1. Review all analyst evidence
2. Construct the bullish thesis — cite specific analyst findings that support upside
3. Identify which vectors (PA, KL, MOM, STR) have the strongest bullish signals
4. Provide UPWARD adjustments where you believe the current scores are too bearish

CRITICAL: You are an ADVOCATE, not a judge. Your job is to make the best bull case possible.
The Bear Researcher will argue the other side. The Risk Manager will arbitrate.

But you must be HONEST — don't fabricate evidence. If there's no bullish case, say so and use small adjustments.

ADJUSTMENT RULES:
  - Each adjustment: -0.15 to +0.15 (you shift, not rescore)
  - Positive adjustments = "the scores should be more bullish"
  - Negative adjustments = "even as the bull, I see weakness here"
  - Cite the analyst whose findings support each adjustment

Respond with ONLY valid JSON:
{{
    "agent_id": "bull_researcher",
    "adjustments": {{
        "price_action": 0.0,
        "key_levels": 0.0,
        "momentum": 0.0,
        "structure": 0.0
    }},
    "confidence": "medium",
    "reasoning": "The bullish thesis in 2-3 sentences, citing analyst evidence",
    "flags": [],
    "strongest_vector": "price_action"
}}

CONFIDENCE: "high" = multiple analysts support the bull case, "medium" = mixed evidence, "low" = bearish data, weak bull case
FLAGS: Optional — "breakout_setup", "momentum_building", "support_holding", "accumulation_pattern"
STRONGEST_VECTOR: Which of the 4 vectors has the best bullish evidence
"""


def build_prompt(context: dict, analyst_reports: list) -> str:
    """Build the bull researcher prompt from context + analyst reports."""
    l1 = context.get("l1_scores", {})
    memory = context.get("memory_context", {})

    # Format analyst reports
    report_lines = []
    for report in analyst_reports:
        agent_id = report.get("agent_id", "unknown")
        confidence = report.get("confidence", "?")
        reasoning = report.get("reasoning", "No reasoning provided")
        adjs = report.get("adjustments", {})
        adj_str = " | ".join(f"{k}:{v:+.3f}" for k, v in adjs.items() if v != 0)
        flags = ", ".join(report.get("flags", [])) or "none"

        report_lines.append(
            f"── {agent_id.upper()} (confidence: {confidence}) ──\n"
            f"  Adjustments: {adj_str or 'all zero'}\n"
            f"  Flags: {flags}\n"
            f"  Analysis: {reasoning}\n"
        )
    analyst_reports_text = "\n".join(report_lines) if report_lines else "(No analyst reports received)"

    # Format memory
    memory_lines = _format_memory(memory)
    memory_text = "\n".join(memory_lines) if memory_lines else "(No memory context)"

    pa = l1.get("price_action", {})
    kl = l1.get("key_levels", {})
    mom = l1.get("momentum", {})
    stru = l1.get("structure", {})

    return BULL_PROMPT_TEMPLATE.format(
        symbol=context.get("symbol", "UNKNOWN"),
        timeframe=context.get("timeframe_label", "15-minute"),
        analyst_reports_text=analyst_reports_text,
        pa_score=_score_val(pa), kl_score=_score_val(kl),
        mom_score=_score_val(mom), str_score=_score_val(stru),
        memory_text=memory_text,
    )


def run_bull_researcher(client, context: dict, model: str,
                        analyst_reports: list = None) -> dict:
    """
    Execute the bull researcher.

    Args:
        client: Anthropic API client
        context: Shared context dict
        model: Model string
        analyst_reports: List of analyst output dicts

    Returns:
        Agent output dict
    """
    analyst_reports = analyst_reports or []
    prompt = build_prompt(context, analyst_reports)
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
            max_tokens=600,
            temperature=0.2,
            messages=[{"role": "user", "content": content}]
        )
        raw = resp.content[0].text.strip()
        clean = re.sub(r'^```json\s*', '', raw)
        clean = re.sub(r'\s*```$', '', clean)
        result = json.loads(clean)

        result.setdefault("agent_id", "bull_researcher")
        result.setdefault("adjustments", {})
        result.setdefault("confidence", "medium")
        result.setdefault("reasoning", "")
        result.setdefault("flags", [])

        # Clamp to ±0.15 (researcher limit)
        for key in ("price_action", "key_levels", "momentum", "structure"):
            val = float(result["adjustments"].get(key, 0))
            result["adjustments"][key] = max(-0.15, min(0.15, val))

        return result

    except json.JSONDecodeError as e:
        logger.warning(f"[BullResearcher] JSON parse failed: {e}")
        return _empty_result("JSON parse error")
    except Exception as e:
        logger.error(f"[BullResearcher] API call failed: {e}")
        return _empty_result(str(e))


def _empty_result(error_msg: str = "") -> dict:
    return {
        "agent_id": "bull_researcher",
        "adjustments": {"price_action": 0.0, "key_levels": 0.0, "momentum": 0.0, "structure": 0.0},
        "confidence": "low",
        "reasoning": f"Agent failed: {error_msg}" if error_msg else "Agent did not respond",
        "flags": ["agent_error"],
    }


def _format_memory(memory: dict) -> list:
    lines = []
    if not memory:
        return lines
    if memory.get("current_markov_state"):
        lines.append(f"State: {memory['current_markov_state']} (held {memory.get('state_duration', '?')} ticks)")
    if memory.get("sentiment_trend"):
        trend = memory["sentiment_trend"]
        lines.append(f"Consensus Trend: {' → '.join(f'{v:+.3f}' for v in trend[-5:])}")
    if memory.get("open_positions"):
        for pos in memory["open_positions"][:3]:
            lines.append(f"Position: {pos.get('direction')} PnL={pos.get('pnl', 0):+.2f}")
    return lines


def _score_val(score_dict) -> float:
    if isinstance(score_dict, dict):
        return float(score_dict.get("score", 0))
    return float(score_dict or 0)
