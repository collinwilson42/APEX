"""
AGENTS — Multi-Agent Decision Framework
========================================
Seed 22: Specialized trading agents for the debate pipeline.
"""

from agents.technical_agent import run_technical_agent
from agents.bull_researcher import run_bull_researcher
from agents.bear_researcher import run_bear_researcher
from agents.risk_gate import run_risk_gate

# Phase 2 agents (imported when available)
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


AGENT_DISPATCH = {
    "technical":        run_technical_agent,
    "key_levels":       run_key_levels_agent,
    "momentum":         run_momentum_agent,
    "sentiment":        run_sentiment_agent,
    "news":             run_news_agent,
    "bull_researcher":  run_bull_researcher,
    "bear_researcher":  run_bear_researcher,
    "risk_gate":        run_risk_gate,
}
