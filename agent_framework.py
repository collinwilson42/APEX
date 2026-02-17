"""
AGENT FRAMEWORK — Multi-Agent Debate Orchestrator
===================================================
Seed 22: Multi-Agent Decision Framework

Orchestrates the full debate pipeline:
  1. Build shared context (L1 scores + indicators + screenshot + memory)
  2. Run analyst agents (parallel)
  3. Run bull/bear researchers (sequential, receive analyst reports)
  4. Synthesize debate → adjustment vector
  5. Run risk gate → multipliers
  6. Produce final output (same format as legacy score_chart)

The output of run_debate() is a DROP-IN replacement for score_chart().
torra_trader.py's _tick() calls this instead and gets back the same dict shape.
"""

import json
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ── Agent imports ──
from agents.technical_agent import run_technical_agent
from agents.bull_researcher import run_bull_researcher
from agents.bear_researcher import run_bear_researcher
from agents.risk_gate import run_risk_gate
from agent_config import (
    resolve_agent_config, get_model_for_agent, AGENT_ROSTER
)

# Phase 2 agents (optional)
try:
    from agents.key_levels_agent import run_key_levels_agent
except ImportError:
    run_key_levels_agent = None

try:
    from agents.momentum_agent import run_momentum_agent
except ImportError:
    run_momentum_agent = None

try:
    from agents.sentiment_agent import run_sentiment_agent
except ImportError:
    run_sentiment_agent = None

try:
    from agents.news_agent import run_news_agent
except ImportError:
    run_news_agent = None

# Agent function dispatch
_ANALYST_DISPATCH = {
    "technical":  run_technical_agent,
    "key_levels": run_key_levels_agent,
    "momentum":   run_momentum_agent,
    "sentiment":  run_sentiment_agent,
    "news":       run_news_agent,
}


# ═══════════════════════════════════════════════════════════════════════════
# MEMORY CONTEXT BUILDER — Torra's Edge
# ═══════════════════════════════════════════════════════════════════════════

BIAS_LABELS = {-2: "Strong Bearish", -1: "Bearish", 0: "Neutral", 1: "Bullish", 2: "Strong Bullish"}


def _safe_int(val, default=0) -> int:
    """Safely convert DB values (may be stored as TEXT) to int."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def build_memory_context(db, instance_id: str, timeframe: str) -> dict:
    """
    Build the memory context from Torra's database — the information
    TradingAgents doesn't have.

    Pulls from: markov_matrices, sentiment history, open positions,
    state transitions, and temporal context.
    """
    memory = {}

    try:
        # ── Markov state ──
        matrix_data = db.get_markov_matrix(instance_id, timeframe)
        if matrix_data:
            current = matrix_data.get("current_state", 0)
            memory["current_markov_state"] = BIAS_LABELS.get(current, "Neutral")
            memory["stability_score"] = matrix_data.get("stability_score")
            memory["trend_bias"] = matrix_data.get("trend_bias")

            # State duration — count how many recent transitions stayed in same state
            transitions = db.get_state_transitions(instance_id, timeframe, limit=10)
            if transitions:
                duration = 0
                for t in transitions:
                    to_st = _safe_int(t.get("to_state", 0))
                    if to_st == current:
                        duration += 1
                    else:
                        break
                memory["state_duration"] = duration
                memory["recent_transitions"] = [
                    f"{BIAS_LABELS.get(_safe_int(t.get('from_state', 0)), '?')}→{BIAS_LABELS.get(_safe_int(t.get('to_state', 0)), '?')}"
                    for t in transitions[:5]
                ]

        # ── Sentiment trend ──
        history = db.get_sentiment_history(instance_id, timeframe, limit=10)
        if history:
            scores = [h.get("consensus_score", 0) for h in history if h.get("consensus_score") is not None]
            if scores:
                scores.reverse()  # oldest first
                memory["sentiment_trend"] = scores

                if len(scores) >= 3:
                    recent_avg = sum(scores[-3:]) / 3
                    older_avg = sum(scores[:3]) / 3
                    if recent_avg > older_avg + 0.05:
                        memory["trend_direction"] = "rising"
                    elif recent_avg < older_avg - 0.05:
                        memory["trend_direction"] = "falling"
                    else:
                        memory["trend_direction"] = "flat"

            # Recent signals
            signals = [h.get("signal_direction", "HOLD") for h in history[:5]]
            signals.reverse()
            memory["recent_signals"] = signals

        # ── Open positions ──
        try:
            positions = db.get_open_positions(instance_id)
            if positions:
                memory["open_positions"] = [
                    {
                        "direction": p.get("direction", "?"),
                        "pnl": float(p.get("unrealized_pnl", 0) or p.get("mt5_profit", 0) or 0),
                        "lots": float(p.get("lots", 0) or 0),
                        "age_ticks": "?",  # Would need entry timestamp comparison
                    }
                    for p in positions[:5]
                ]
            else:
                memory["open_positions"] = []
        except Exception:
            memory["open_positions"] = []

        # ── Temporal context ──
        now = datetime.now()
        memory["day_of_week"] = now.strftime("%A")
        hour = now.hour

        if 0 <= hour < 8:
            memory["session"] = "ASIA"
        elif 8 <= hour < 13:
            memory["session"] = "LONDON"
        elif 13 <= hour < 16:
            memory["session"] = "LONDON_NY_OVERLAP"
        elif 16 <= hour < 21:
            memory["session"] = "NEW_YORK"
        else:
            memory["session"] = "AFTER_HOURS"

    except Exception as e:
        logger.warning(f"[Memory] Failed to build context: {e}")

    return memory


# ═══════════════════════════════════════════════════════════════════════════
# DEBATE SYNTHESIS
# ═══════════════════════════════════════════════════════════════════════════

VECTORS = ("price_action", "key_levels", "momentum", "structure")


def _synthesize_analysts(analyst_results: List[dict]) -> dict:
    """
    Average analyst adjustments, weighted by confidence.
    """
    conf_weights = {"high": 1.0, "medium": 0.6, "low": 0.3}
    totals = {v: 0.0 for v in VECTORS}
    weights = {v: 0.0 for v in VECTORS}

    for result in analyst_results:
        if "agent_error" in result.get("flags", []):
            continue
        conf = conf_weights.get(result.get("confidence", "medium"), 0.6)
        adjs = result.get("adjustments", {})

        for v in VECTORS:
            val = float(adjs.get(v, 0))
            if val != 0:
                totals[v] += val * conf
                weights[v] += conf
            else:
                # Zero adjustments still count as a data point (agreement)
                weights[v] += conf * 0.5

    consensus = {}
    for v in VECTORS:
        if weights[v] > 0:
            consensus[v] = totals[v] / weights[v]
        else:
            consensus[v] = 0.0

    return consensus


def _synthesize_debate(analyst_consensus: dict,
                       bull_result: dict,
                       bear_result: dict,
                       max_shift: float = 0.15) -> dict:
    """
    Combine analyst consensus with researcher arguments.

    For each vector:
      debate_score = analyst_avg + (bull_adj + bear_adj) / 2
    """
    debate = {}
    bull_adjs = bull_result.get("adjustments", {})
    bear_adjs = bear_result.get("adjustments", {})

    for v in VECTORS:
        base = analyst_consensus.get(v, 0.0)
        bull_shift = max(-max_shift, min(max_shift, float(bull_adjs.get(v, 0))))
        bear_shift = max(-max_shift, min(max_shift, float(bear_adjs.get(v, 0))))
        debate[v] = base + (bull_shift + bear_shift) / 2.0

    return debate


def _apply_risk_gate(debate_adjustments: dict, risk_result: dict) -> dict:
    """
    Apply risk gate multipliers to debate adjustments.
    """
    multipliers = risk_result.get("multipliers", {})
    final = {}

    for v in VECTORS:
        adj = debate_adjustments.get(v, 0.0)
        mult = float(multipliers.get(v, 1.0))
        final[v] = adj * mult

    return final


def _clamp_adjustments(adjustments: dict, max_adj: float = 0.3) -> dict:
    """Final clamp to ±max_adj (Seed 21 constraint)."""
    return {v: max(-max_adj, min(max_adj, adjustments.get(v, 0.0))) for v in VECTORS}


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE — run_debate()
# ═══════════════════════════════════════════════════════════════════════════

def run_debate(client, context: dict, agent_config: dict = None,
               db=None, instance_id: str = None) -> dict:
    """
    Execute the full multi-agent debate pipeline.

    This is the DROP-IN replacement for score_chart().

    Args:
        client:         Anthropic API client
        context:        Shared context dict with keys:
                          - symbol, timeframe_label
                          - screenshot_b64 (base64 PNG or None)
                          - l1_scores (dict from technical_calculator, or empty)
                          - indicator_snapshot (raw indicator values, or empty)
        agent_config:   Agent configuration (from resolve_agent_config)
        db:             InstanceDatabaseManager (for memory context)
        instance_id:    Instance ID (for memory context)

    Returns:
        Dict matching score_chart() output format:
        {
            "price_action": {"score": float, "note": str},
            "key_levels":   {"score": float, "note": str},
            "momentum":     {"score": float, "note": str},
            "structure":    {"score": float, "note": str},
            "composite_bias": {"score": float, "note": str},
            "agent_deliberation": { ... full debug data ... }
        }
    """
    from agent_config import DEFAULT_AGENT_CONFIG, resolve_agent_config as _resolve

    config = agent_config or _resolve()
    timeout = config.get("timeout_seconds", 15)
    active = config.get("active_agents", ["technical", "bull_researcher", "bear_researcher", "risk_gate"])
    max_shift = config.get("max_researcher_shift", 0.15)
    max_adj = config.get("max_total_adjustment", 0.30)

    start_time = time.time()
    deliberation = {
        "mode": config.get("mode", "budget"),
        "active_agents": active,
        "analyst_reports": [],
        "bull_result": None,
        "bear_result": None,
        "risk_result": None,
        "timing": {},
    }

    # ── Build memory context (Torra's edge) ──
    if config.get("include_markov_context", True) and db and instance_id:
        timeframe = "15m" if "15" in context.get("timeframe_label", "15") else "1h"
        memory = build_memory_context(db, instance_id, timeframe)
        context["memory_context"] = memory
    else:
        context.setdefault("memory_context", {})

    # ══════════════════════════════════════════════════════════════════
    # PHASE 1: Run analyst agents (parallel)
    # ══════════════════════════════════════════════════════════════════
    analyst_ids = [a for a in active if AGENT_ROSTER.get(a, {}).get("role") == "analyst"]
    analyst_results = []

    t0 = time.time()
    if analyst_ids:
        with ThreadPoolExecutor(max_workers=min(len(analyst_ids), 5)) as executor:
            futures = {}
            for agent_id in analyst_ids:
                fn = _ANALYST_DISPATCH.get(agent_id)
                if fn is None:
                    logger.info(f"[Framework] Skipping {agent_id} (not installed)")
                    continue
                model = get_model_for_agent(agent_id, config)
                futures[executor.submit(fn, client, context, model)] = agent_id

            for future in as_completed(futures, timeout=timeout):
                agent_id = futures[future]
                try:
                    result = future.result(timeout=2)
                    analyst_results.append(result)
                    logger.info(f"  🔹 {agent_id}: conf={result.get('confidence')} "
                               f"flags={result.get('flags', [])}")
                except Exception as e:
                    logger.warning(f"  ✗ {agent_id} failed: {e}")
                    analyst_results.append({
                        "agent_id": agent_id,
                        "adjustments": {v: 0.0 for v in VECTORS},
                        "confidence": "low",
                        "reasoning": f"Agent timed out or failed: {e}",
                        "flags": ["agent_error"],
                    })

    deliberation["analyst_reports"] = analyst_results
    deliberation["timing"]["analysts_ms"] = int((time.time() - t0) * 1000)

    # ── Synthesize analyst consensus ──
    analyst_consensus = _synthesize_analysts(analyst_results)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 2: Run bull/bear researchers (sequential)
    # ══════════════════════════════════════════════════════════════════
    bull_result = {"agent_id": "bull_researcher", "adjustments": {v: 0.0 for v in VECTORS},
                   "confidence": "low", "reasoning": "Not active", "flags": []}
    bear_result = {"agent_id": "bear_researcher", "adjustments": {v: 0.0 for v in VECTORS},
                   "confidence": "low", "reasoning": "Not active", "flags": []}

    t1 = time.time()
    elapsed_so_far = t1 - start_time
    remaining_timeout = max(timeout - elapsed_so_far - 2, 3)  # Reserve 2s for risk gate

    if "bull_researcher" in active:
        try:
            model = get_model_for_agent("bull_researcher", config)
            bull_result = run_bull_researcher(client, context, model, analyst_results)
            logger.info(f"  🐂 Bull: conf={bull_result.get('confidence')} "
                       f"strongest={bull_result.get('strongest_vector', '?')}")
        except Exception as e:
            logger.warning(f"  ✗ Bull researcher failed: {e}")

    if "bear_researcher" in active:
        try:
            model = get_model_for_agent("bear_researcher", config)
            bear_result = run_bear_researcher(client, context, model, analyst_results)
            logger.info(f"  🐻 Bear: conf={bear_result.get('confidence')} "
                       f"weakest={bear_result.get('weakest_vector', '?')}")
        except Exception as e:
            logger.warning(f"  ✗ Bear researcher failed: {e}")

    deliberation["bull_result"] = bull_result
    deliberation["bear_result"] = bear_result
    deliberation["timing"]["researchers_ms"] = int((time.time() - t1) * 1000)

    # ── Synthesize debate ──
    debate_adjustments = _synthesize_debate(analyst_consensus, bull_result, bear_result, max_shift)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 3: Risk Gate
    # ══════════════════════════════════════════════════════════════════
    risk_result = {"agent_id": "risk_gate", "multipliers": {v: 1.0 for v in VECTORS},
                   "overall_risk_level": "unknown", "reasoning": "Not active",
                   "flags": [], "veto": False}

    t2 = time.time()

    # Collect all flags from all agents
    all_flags = []
    for r in analyst_results:
        all_flags.extend(r.get("flags", []))
    all_flags.extend(bull_result.get("flags", []))
    all_flags.extend(bear_result.get("flags", []))
    all_flags = [f for f in all_flags if f != "agent_error"]  # Don't pass meta-flags

    if "risk_gate" in active:
        try:
            model = get_model_for_agent("risk_gate", config)
            risk_result = run_risk_gate(
                client, context, model,
                debate_adjustments=debate_adjustments,
                bull_result=bull_result,
                bear_result=bear_result,
                all_flags=all_flags,
            )
            logger.info(f"  🛡️  Risk: level={risk_result.get('overall_risk_level')} "
                       f"veto={risk_result.get('veto', False)}")
        except Exception as e:
            logger.warning(f"  ✗ Risk gate failed: {e}")

    deliberation["risk_result"] = risk_result
    deliberation["timing"]["risk_gate_ms"] = int((time.time() - t2) * 1000)

    # ══════════════════════════════════════════════════════════════════
    # PHASE 4: Final adjustment computation
    # ══════════════════════════════════════════════════════════════════
    gated_adjustments = _apply_risk_gate(debate_adjustments, risk_result)
    final_adjustments = _clamp_adjustments(gated_adjustments, max_adj)

    total_ms = int((time.time() - start_time) * 1000)
    deliberation["timing"]["total_ms"] = total_ms
    deliberation["final_adjustments"] = final_adjustments
    deliberation["debate_adjustments"] = debate_adjustments
    deliberation["analyst_consensus"] = analyst_consensus

    # ══════════════════════════════════════════════════════════════════
    # OUTPUT: Match score_chart() format exactly
    # ══════════════════════════════════════════════════════════════════
    # These are ADJUSTMENTS, not absolute scores.
    # torra_trader will blend: final = L1 * 0.80 + agent_adj * 0.20
    # But to maintain backward compat with the score_chart() interface,
    # we return them as "scores" — the trader knows they're adjustments
    # because source_type will be "AGENT_DEBATE"

    avg_adj = sum(final_adjustments.values()) / 4.0
    risk_level = risk_result.get("overall_risk_level", "unknown")
    veto = risk_result.get("veto", False)

    # Build composite note from debate
    bull_conf = bull_result.get("confidence", "?")
    bear_conf = bear_result.get("confidence", "?")
    note_parts = [
        f"Debate: 🐂{bull_conf}/🐻{bear_conf}",
        f"Risk:{risk_level}",
        f"{len(analyst_results)} analysts",
        f"{total_ms}ms",
    ]
    if veto:
        note_parts.insert(0, "⛔ VETOED")
    if all_flags:
        note_parts.append(f"flags:[{','.join(all_flags[:3])}]")

    output = {
        "price_action": {
            "score": final_adjustments["price_action"],
            "note": _build_vector_note("PA", final_adjustments["price_action"],
                                       analyst_consensus.get("price_action", 0),
                                       risk_result.get("multipliers", {}).get("price_action", 1)),
        },
        "key_levels": {
            "score": final_adjustments["key_levels"],
            "note": _build_vector_note("KL", final_adjustments["key_levels"],
                                       analyst_consensus.get("key_levels", 0),
                                       risk_result.get("multipliers", {}).get("key_levels", 1)),
        },
        "momentum": {
            "score": final_adjustments["momentum"],
            "note": _build_vector_note("MOM", final_adjustments["momentum"],
                                       analyst_consensus.get("momentum", 0),
                                       risk_result.get("multipliers", {}).get("momentum", 1)),
        },
        "structure": {
            "score": final_adjustments["structure"],
            "note": _build_vector_note("STR", final_adjustments["structure"],
                                       analyst_consensus.get("structure", 0),
                                       risk_result.get("multipliers", {}).get("structure", 1)),
        },
        "composite_bias": {
            "score": avg_adj,
            "note": " | ".join(note_parts),
        },
        # Extra data — stored in agent_deliberation column
        "agent_deliberation": deliberation,
    }

    logger.info(f"  ⚖️  Final: PA={final_adjustments['price_action']:+.3f} "
               f"KL={final_adjustments['key_levels']:+.3f} "
               f"MOM={final_adjustments['momentum']:+.3f} "
               f"STR={final_adjustments['structure']:+.3f} "
               f"| {total_ms}ms | risk={risk_level}")

    return output


def _build_vector_note(label: str, final: float, consensus: float, risk_mult: float) -> str:
    """Build a compact note for each vector."""
    parts = [f"adj={final:+.3f}"]
    if abs(consensus - final) > 0.01:
        parts.append(f"pre-risk={consensus:+.3f}")
    if risk_mult < 0.99:
        parts.append(f"risk×{risk_mult:.2f}")
    return f"{label}: {' '.join(parts)}"
