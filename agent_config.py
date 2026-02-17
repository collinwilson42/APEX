"""
AGENT CONFIG — Multi-Agent Decision Framework Configuration
=============================================================
Seed 22: Multi-Agent Decision Framework

Defines agent roles, model assignments, cost controls, and debate parameters.
Loaded by agent_framework.py. Can be overridden per-profile via trading_config["agents"].
"""

# ═══════════════════════════════════════════════════════════════════════════
# MODEL ASSIGNMENTS
# ═══════════════════════════════════════════════════════════════════════════

# Quick-think: cheap, fast — for analyst data gathering
QUICK_THINK_MODEL = "claude-haiku-4-5-20251001"

# Deep-think: expensive, thorough — for researchers and risk gate
DEEP_THINK_MODEL = "claude-sonnet-4-20250514"


# ═══════════════════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

AGENT_ROSTER = {
    # ── Analysts (parallel, quick-think) ──
    "technical": {
        "name": "Technical Analyst",
        "role": "analyst",
        "model_tier": "quick",
        "primary_vectors": ["price_action", "structure"],
        "description": "Interprets chart patterns, candle formations, and trend structure",
    },
    "key_levels": {
        "name": "Key Levels Specialist",
        "role": "analyst",
        "model_tier": "quick",
        "primary_vectors": ["key_levels"],
        "description": "Fibonacci, Bollinger, Ichimoku cloud, support/resistance analysis",
    },
    "momentum": {
        "name": "Momentum Specialist",
        "role": "analyst",
        "model_tier": "quick",
        "primary_vectors": ["momentum"],
        "description": "RSI, MACD, Stochastic, CCI, ADX deep analysis",
    },
    "sentiment": {
        "name": "Sentiment Analyst",
        "role": "analyst",
        "model_tier": "quick",
        "primary_vectors": ["price_action", "key_levels", "momentum", "structure"],
        "description": "Market mood overlay from price behavior and context",
    },
    "news": {
        "name": "News Analyst",
        "role": "analyst",
        "model_tier": "quick",
        "primary_vectors": ["price_action", "momentum"],
        "description": "PrimoGPT-style NLP feature extraction from financial news",
    },

    # ── Researchers (sequential after analysts, deep-think) ──
    "bull_researcher": {
        "name": "Bull Researcher",
        "role": "researcher",
        "model_tier": "deep",
        "description": "Argues the bullish case from all analyst reports",
    },
    "bear_researcher": {
        "name": "Bear Researcher",
        "role": "researcher",
        "model_tier": "deep",
        "description": "Argues the bearish case from all analyst reports",
    },

    # ── Risk Gate (final, deep-think) ──
    "risk_gate": {
        "name": "Risk Manager",
        "role": "gate",
        "model_tier": "deep",
        "description": "Can VETO or ATTENUATE signals based on risk assessment",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PRESET MODES
# ═══════════════════════════════════════════════════════════════════════════

MODE_PRESETS = {
    "budget": {
        "active_agents": [
            "technical",
            "bull_researcher",
            "bear_researcher",
            "risk_gate",
        ],
        "debate_rounds": 1,
        "timeout_seconds": 15,
        "description": "4 agents: Tech analyst + Bull/Bear debate + Risk gate",
    },
    "standard": {
        "active_agents": [
            "technical",
            "key_levels",
            "momentum",
            "bull_researcher",
            "bear_researcher",
            "risk_gate",
        ],
        "debate_rounds": 1,
        "timeout_seconds": 18,
        "description": "6 agents: 3 analysts + Bull/Bear debate + Risk gate",
    },
    "full": {
        "active_agents": [
            "technical",
            "key_levels",
            "momentum",
            "sentiment",
            "news",
            "bull_researcher",
            "bear_researcher",
            "risk_gate",
        ],
        "debate_rounds": 2,
        "timeout_seconds": 25,
        "description": "8 agents: All 5 analysts + Bull/Bear debate + Risk gate",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT AGENT CONFIG (merged into trading_config["agents"])
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_AGENT_CONFIG = {
    "enabled": True,
    "mode": "budget",
    "active_agents": MODE_PRESETS["budget"]["active_agents"],
    "debate_rounds": 1,
    "quick_think_model": QUICK_THINK_MODEL,
    "deep_think_model": DEEP_THINK_MODEL,
    "max_api_cost_per_hour": 2.00,
    "timeout_seconds": 15,
    "include_news": False,
    "include_markov_context": True,
    "include_sentiment_history": True,
    "history_lookback": 10,
    # Debate constraints
    "max_researcher_shift": 0.15,   # Max ± a researcher can shift a vector
    "max_total_adjustment": 0.30,   # Final clamp (matches Seed 21)
    "risk_gate_min_multiplier": 0.0,  # Risk gate can zero out (full veto)
    "risk_gate_max_multiplier": 1.0,  # Risk gate cannot amplify
}


def resolve_agent_config(profile_config: dict = None) -> dict:
    """
    Merge profile-level agent config with defaults.
    
    Args:
        profile_config: trading_config.get("agents", {}) from the profile
        
    Returns:
        Complete agent config dict
    """
    config = DEFAULT_AGENT_CONFIG.copy()
    
    if profile_config:
        # Apply mode preset first if mode changed
        mode = profile_config.get("mode", config["mode"])
        if mode in MODE_PRESETS and mode != config["mode"]:
            preset = MODE_PRESETS[mode]
            config["active_agents"] = preset["active_agents"]
            config["debate_rounds"] = preset["debate_rounds"]
            config["timeout_seconds"] = preset["timeout_seconds"]
            config["mode"] = mode
        
        # Then overlay any explicit overrides
        for key, value in profile_config.items():
            if key in config and value is not None:
                config[key] = value
    
    return config


def get_model_for_agent(agent_id: str, agent_config: dict) -> str:
    """Get the LLM model string for a given agent based on its tier."""
    roster_entry = AGENT_ROSTER.get(agent_id, {})
    tier = roster_entry.get("model_tier", "quick")
    
    if tier == "deep":
        return agent_config.get("deep_think_model", DEEP_THINK_MODEL)
    else:
        return agent_config.get("quick_think_model", QUICK_THINK_MODEL)
