"""
API DECISION ENGINE
Every minute: Screenshot + Data → Claude API → Δ±1 Decision
Simple, effective position management
"""

import os
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import anthropic


class APIDecisionEngine:
    """
    Sends market data to Claude API for position sizing decisions
    Returns: Δ±1 (increase/decrease position by 1 lot)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize API Decision Engine
        
        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("API key required. Set ANTHROPIC_API_KEY or pass api_key parameter")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.decisions_made = 0
        
    def analyze_market(
        self,
        screenshot_path: str,
        trade_score: float,
        current_position: float,
        current_sl: Optional[float],
        current_tp: Optional[float],
        current_price: float,
        risk_reward_level: int,
        chart_data_15m: Dict[str, Any],
        chart_data_1m: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze market and make Δ±1 decision
        
        Args:
            screenshot_path: Path to latest chart screenshot
            trade_score: Current trade score (0-100)
            current_position: Current position size (negative = short, positive = long)
            current_sl: Current stop loss price (None if not set)
            current_tp: Current take profit price (None if not set)
            current_price: Current market price
            risk_reward_level: Risk tolerance (0=conservative, 100=aggressive)
            chart_data_15m: Latest 15m bar data
            chart_data_1m: Latest 1m bar data
            account_info: Account balance/equity info
        
        Returns:
            Dictionary with:
            - decision: -1 (decrease), 0 (hold), +1 (increase)
            - reasoning: Explanation
            - new_sl: Recommended SL (None if no change)
            - new_tp: Recommended TP (None if no change)
            - confidence: Decision confidence (0-100)
        """
        try:
            # Read and encode screenshot
            with open(screenshot_path, 'rb') as f:
                screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Build market context
            context = self._build_market_context(
                trade_score=trade_score,
                current_position=current_position,
                current_sl=current_sl,
                current_tp=current_tp,
                current_price=current_price,
                risk_reward_level=risk_reward_level,
                chart_data_15m=chart_data_15m,
                chart_data_1m=chart_data_1m,
                account_info=account_info
            )
            
            # Build prompt
            prompt = self._build_decision_prompt(context)
            
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_b64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Parse response
            response_text = message.content[0].text
            decision = self._parse_api_response(response_text, context)
            
            self.decisions_made += 1
            
            print(f"\n{'='*70}")
            print(f"API DECISION #{self.decisions_made}")
            print(f"{'='*70}")
            print(f"Decision: {decision['decision']:+d}")
            print(f"Confidence: {decision['confidence']}%")
            print(f"Reasoning: {decision['reasoning']}")
            if decision['new_sl']:
                print(f"New SL: ${decision['new_sl']:.2f}")
            if decision['new_tp']:
                print(f"New TP: ${decision['new_tp']:.2f}")
            print(f"{'='*70}\n")
            
            return decision
            
        except Exception as e:
            print(f"✗ API Decision Engine error: {e}")
            import traceback
            traceback.print_exc()
            
            # Return safe default (hold)
            return {
                'decision': 0,
                'reasoning': f'Error occurred: {str(e)}',
                'new_sl': None,
                'new_tp': None,
                'confidence': 0
            }
    
    def _build_market_context(
        self,
        trade_score: float,
        current_position: float,
        current_sl: Optional[float],
        current_tp: Optional[float],
        current_price: float,
        risk_reward_level: int,
        chart_data_15m: Dict[str, Any],
        chart_data_1m: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> str:
        """Build formatted market context string"""
        
        # Position direction
        if current_position > 0.1:
            position_str = f"+{current_position:.1f} lots (LONG)"
        elif current_position < -0.1:
            position_str = f"{current_position:.1f} lots (SHORT)"
        else:
            position_str = "FLAT"
        
        # SL/TP status
        sl_str = f"${current_sl:.2f}" if current_sl and current_sl > 0 else "Not set"
        tp_str = f"${current_tp:.2f}" if current_tp and current_tp > 0 else "Not set"
        
        # Risk/Reward interpretation
        if risk_reward_level >= 80:
            rr_desc = "AGGRESSIVE (80-100)"
        elif risk_reward_level >= 60:
            rr_desc = "MODERATE-HIGH (60-79)"
        elif risk_reward_level >= 40:
            rr_desc = "BALANCED (40-59)"
        elif risk_reward_level >= 20:
            rr_desc = "CONSERVATIVE (20-39)"
        else:
            rr_desc = "VERY CONSERVATIVE (0-19)"
        
        context = f"""MARKET SNAPSHOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CURRENT POSITION:
- Size: {position_str}
- Entry: See chart for position markers
- SL: {sl_str}
- TP: {tp_str}
- Current P&L: ${account_info.get('profit', 0):.2f}

TRADE SCORE: {trade_score:.1f}/100
RISK/REWARD LEVEL: {risk_reward_level} ({rr_desc})
CURRENT PRICE: ${current_price:.2f}

15M CHART DATA:
- Supertrend: {chart_data_15m.get('supertrend', 'N/A')}
- ATR: {chart_data_15m.get('atr_14', 0):.2f}
- ATR Ratio: {chart_data_15m.get('atr_ratio', 0):.2f}
- EMA Distance: {chart_data_15m.get('ema_distance', 0):.2f}
- Fib Zone: {chart_data_15m.get('current_fib_zone', 'N/A')}

1M CHART DATA:
- Supertrend: {chart_data_1m.get('supertrend', 'N/A')}
- ATR: {chart_data_1m.get('atr_14', 0):.2f}
- Recent Momentum: See chart

ACCOUNT:
- Balance: ${account_info.get('balance', 0):.2f}
- Equity: ${account_info.get('equity', 0):.2f}
- Margin Level: {account_info.get('margin_level', 0):.1f}%
"""
        return context
    
    def _build_decision_prompt(self, context: str) -> str:
        """Build decision prompt for Claude"""
        
        return f"""{context}

TASK: Analyze the chart screenshot and data above. Make a SINGLE decision:

Δ = -1  (Decrease position by 1 lot)
Δ = 0   (Hold current position)
Δ = +1  (Increase position by 1 lot)

RULES:
1. If FLAT and bullish → consider Δ+1 to go LONG
2. If FLAT and bearish → consider Δ+1 to go SHORT (via SELL)
3. If LONG and very bullish → consider Δ+1 to add
4. If LONG but weakening → consider Δ-1 to scale out
5. If SHORT and very bearish → consider Δ+1 to add
6. If SHORT but weakening → consider Δ-1 to cover
7. Risk/Reward Level affects aggression: higher = more willing to add, lower = more cautious

RESPOND IN THIS EXACT FORMAT:
DECISION: [+1, 0, or -1]
CONFIDENCE: [0-100]
REASONING: [One clear sentence explaining why]
NEW_SL: [price or NONE]
NEW_TP: [price or NONE]

Example:
DECISION: +1
CONFIDENCE: 75
REASONING: Strong 15m uptrend with consolidation on 1m, score 72 supports adding to position.
NEW_SL: 2025.50
NEW_TP: 2075.00
"""
    
    def _parse_api_response(self, response: str, context: str) -> Dict[str, Any]:
        """Parse Claude's response into structured decision"""
        
        try:
            lines = response.strip().split('\n')
            
            decision = 0
            confidence = 50
            reasoning = "API parsing incomplete"
            new_sl = None
            new_tp = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('DECISION:'):
                    dec_str = line.split(':', 1)[1].strip()
                    if '+1' in dec_str:
                        decision = 1
                    elif '-1' in dec_str:
                        decision = -1
                    else:
                        decision = 0
                
                elif line.startswith('CONFIDENCE:'):
                    conf_str = line.split(':', 1)[1].strip()
                    try:
                        confidence = int(conf_str.replace('%', ''))
                    except:
                        confidence = 50
                
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
                
                elif line.startswith('NEW_SL:'):
                    sl_str = line.split(':', 1)[1].strip()
                    if 'NONE' not in sl_str.upper():
                        try:
                            new_sl = float(sl_str.replace('$', '').replace(',', ''))
                        except:
                            new_sl = None
                
                elif line.startswith('NEW_TP:'):
                    tp_str = line.split(':', 1)[1].strip()
                    if 'NONE' not in tp_str.upper():
                        try:
                            new_tp = float(tp_str.replace('$', '').replace(',', ''))
                        except:
                            new_tp = None
            
            return {
                'decision': decision,
                'confidence': confidence,
                'reasoning': reasoning,
                'new_sl': new_sl,
                'new_tp': new_tp
            }
            
        except Exception as e:
            print(f"⚠️  Response parsing error: {e}")
            print(f"Raw response:\n{response}")
            
            return {
                'decision': 0,
                'confidence': 0,
                'reasoning': f'Parsing failed: {str(e)}',
                'new_sl': None,
                'new_tp': None
            }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("API DECISION ENGINE TEST")
    print("="*70)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n✗ ANTHROPIC_API_KEY not set in environment")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        exit(1)
    
    print("✓ API key found")
    
    # Create engine
    engine = APIDecisionEngine()
    
    # Mock test data
    print("\n⚠️  This is a mock test. Provide actual screenshot and data for real testing.")
    
    # You would call it like this:
    # decision = engine.analyze_market(
    #     screenshot_path="latest_screenshot.png",
    #     trade_score=72.5,
    #     current_position=2.0,
    #     current_sl=2025.50,
    #     current_tp=2075.00,
    #     current_price=2050.00,
    #     risk_reward_level=75,
    #     chart_data_15m={'supertrend': 'BULL', 'atr_14': 5.2, ...},
    #     chart_data_1m={'supertrend': 'BULL', 'atr_14': 2.1, ...},
    #     account_info={'balance': 10000, 'equity': 10150, ...}
    # )
    
    print("\n✓ Engine initialized and ready")
    print("="*70)
