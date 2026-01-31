"""
MT5 META AGENT V3.1 - VISION ANALYZER
Uses Claude API to analyze MT5 chart screenshots
Extracts directional confidence, risk levels, and market intelligence
"""

import anthropic
import base64
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Anthropic API Configuration
# Set your API key here or as environment variable
API_KEY = "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"

MODEL = "claude-sonnet-4-20250514"  # Latest Sonnet 4.5
MAX_TOKENS = 2000

# Analysis prompt template
ANALYSIS_PROMPT = """You are an expert algorithmic trading analyst specializing in gold futures (XAUUSD) technical analysis.

Analyze this 15-minute chart screenshot and provide a comprehensive market intelligence assessment.

Your analysis must include:

1. **DIRECTIONAL CONFIDENCE** (0-100 for each):
   - Bullish confidence score
   - Bearish confidence score  
   - Neutral confidence score
   - Primary direction (BULL/BEAR/NEUTRAL)

2. **RISK ASSESSMENT**:
   - Risk level (LOW/MEDIUM/HIGH)
   - Risk score (0-100)
   - Key risk factors

3. **KEY LEVELS**:
   - Resistance levels (list up to 3)
   - Support levels (list up to 3)

4. **NEXT 15M PREDICTION**:
   - Predicted direction for next bar
   - Confidence percentage (0-100)
   - Expected price range

5. **PATTERN RECOGNITION**:
   - Technical patterns detected
   - Trend strength (WEAK/MODERATE/STRONG)

6. **MARKET CONTEXT**:
   - Market regime (TRENDING_BULL/TRENDING_BEAR/RANGING/VOLATILE)
   - Volatility assessment (LOW/NORMAL/HIGH/EXTREME)

7. **SNAPSHOT ANALYSIS** (2-3 paragraph summary):
   Write a clear, actionable summary of the current market state suitable for both human traders and AI systems.

Return your analysis in JSON format with this exact structure:
{
  "directional_confidence": {
    "bullish": 0-100,
    "bearish": 0-100,
    "neutral": 0-100,
    "primary_direction": "BULL|BEAR|NEUTRAL"
  },
  "risk_assessment": {
    "risk_level": "LOW|MEDIUM|HIGH",
    "risk_score": 0-100,
    "risk_factors": ["factor1", "factor2"]
  },
  "key_levels": {
    "resistance": [price1, price2, price3],
    "support": [price1, price2, price3]
  },
  "next_15m_prediction": {
    "direction": "UP|DOWN|SIDEWAYS",
    "confidence": 0-100,
    "expected_range": {"low": price, "high": price}
  },
  "pattern_recognition": {
    "patterns": ["pattern1", "pattern2"],
    "trend_strength": "WEAK|MODERATE|STRONG"
  },
  "market_context": {
    "regime": "TRENDING_BULL|TRENDING_BEAR|RANGING|VOLATILE",
    "volatility": "LOW|NORMAL|HIGH|EXTREME"
  },
  "snapshot_analysis": "Your detailed 2-3 paragraph summary here..."
}

Be precise, quantitative, and actionable. Base your analysis strictly on what you observe in the chart."""

class VisionAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Vision Analyzer with Anthropic API"""
        
        # Get API key from parameter, global variable, or environment
        if api_key:
            self.api_key = api_key
        elif API_KEY:
            self.api_key = API_KEY
        else:
            import os
            self.api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.analysis_count = 0
        
    def encode_image(self, image_path: str) -> tuple[str, str]:
        """
        Encode image to base64 for Claude API
        
        Returns:
            Tuple of (base64_data, media_type)
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError("Image not found: {}".format(image_path))
        
        # Determine media type
        suffix = path.suffix.lower()
        media_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif'
        }
        
        media_type = media_type_map.get(suffix, 'image/png')
        
        # Read and encode image
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.standard_b64encode(image_data).decode('utf-8')
        
        return base64_data, media_type
    
    def analyze_chart(self, image_path: str) -> Dict:
        """
        Analyze chart screenshot using Claude Vision
        
        Args:
            image_path: Path to screenshot file
        
        Returns:
            Dictionary with complete analysis results
        """
        start_time = time.time()
        
        try:
            print("\n" + "="*70)
            print("ANALYZING CHART: {}".format(Path(image_path).name))
            print("="*70)
            
            # Encode image
            print("Encoding image...")
            base64_data, media_type = self.encode_image(image_path)
            image_size_kb = len(base64_data) / 1024 * 0.75  # Approximate decoded size
            print("[OK] Image encoded ({:.1f} KB)".format(image_size_kb))
            
            # Call Claude API
            print("Calling Claude API ({})...".format(MODEL))
            
            message = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data
                                }
                            },
                            {
                                "type": "text",
                                "text": ANALYSIS_PROMPT
                            }
                        ]
                    }
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            
            # Parse JSON response
            print("Parsing analysis...")
            
            # Try to extract JSON from response (might have markdown formatting)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                analysis = json.loads(json_text)
            else:
                # If no JSON found, return raw text
                analysis = {
                    "snapshot_analysis": response_text,
                    "error": "Could not parse structured JSON response"
                }
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add metadata
            analysis['metadata'] = {
                'image_path': str(image_path),
                'analysis_timestamp': datetime.now().isoformat(),
                'duration_ms': duration_ms,
                'model_version': MODEL,
                'tokens_used': message.usage.input_tokens + message.usage.output_tokens
            }
            
            self.analysis_count += 1
            
            # Print summary
            print("[OK] Analysis complete ({}ms)".format(duration_ms))
            print("\nKey Results:")
            
            if 'directional_confidence' in analysis:
                dc = analysis['directional_confidence']
                print("  Direction: {}".format(dc.get('primary_direction', 'N/A')))
                print("  Confidence: Bull={} | Bear={} | Neutral={}".format(
                    dc.get('bullish', 0),
                    dc.get('bearish', 0),
                    dc.get('neutral', 0)
                ))
            
            if 'risk_assessment' in analysis:
                ra = analysis['risk_assessment']
                print("  Risk: {} (Score: {})".format(
                    ra.get('risk_level', 'N/A'),
                    ra.get('risk_score', 0)
                ))
            
            if 'market_context' in analysis:
                mc = analysis['market_context']
                print("  Regime: {}".format(mc.get('regime', 'N/A')))
                print("  Volatility: {}".format(mc.get('volatility', 'N/A')))
            
            print("\nSnapshot Analysis Preview:")
            if 'snapshot_analysis' in analysis:
                preview = analysis['snapshot_analysis'][:200] + "..."
                print("  {}".format(preview))
            
            print("="*70)
            
            return analysis
            
        except json.JSONDecodeError as e:
            print("[ERROR] JSON parsing error: {}".format(e))
            print("Raw response: {}".format(response_text[:500]))
            raise
            
        except Exception as e:
            print("[ERROR] Analysis error: {}".format(e))
            raise
    
    def analyze_and_save(self, image_path: str, output_path: Optional[str] = None) -> Dict:
        """
        Analyze chart and save results to JSON file
        
        Args:
            image_path: Path to screenshot
            output_path: Path to save JSON (optional, auto-generated if None)
        
        Returns:
            Analysis dictionary
        """
        # Perform analysis
        analysis = self.analyze_chart(image_path)
        
        # Generate output path if not provided
        if output_path is None:
            image_path_obj = Path(image_path)
            output_path = image_path_obj.with_suffix('.json')
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print("\n[OK] Analysis saved to: {}".format(output_path))
        
        return analysis

def test_analyzer():
    """Test the vision analyzer with a sample screenshot"""
    
    print("="*70)
    print("VISION ANALYZER TEST")
    print("="*70)
    
    # Check for screenshots
    screenshot_dir = Path("screenshots")
    if not screenshot_dir.exists():
        print("\n[ERROR] Screenshot directory not found: {}".format(screenshot_dir))
        print("Run screenshot_capture.py first to capture a chart screenshot.")
        return
    
    # Find most recent screenshot
    screenshots = sorted(screenshot_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not screenshots:
        print("\n[ERROR] No screenshots found in {}".format(screenshot_dir))
        print("Run screenshot_capture.py first.")
        return
    
    latest_screenshot = screenshots[0]
    print("\nUsing latest screenshot: {}".format(latest_screenshot.name))
    
    # Initialize analyzer
    try:
        analyzer = VisionAnalyzer()
        
        # Analyze
        analysis = analyzer.analyze_and_save(str(latest_screenshot))
        
        print("\n" + "="*70)
        print("[OK] TEST SUCCESSFUL")
        print("="*70)
        
    except ValueError as e:
        print("\n[ERROR] Configuration error: {}".format(e))
        print("\nSet your Anthropic API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        print("Or pass it as parameter to VisionAnalyzer(api_key='...')")
        
    except Exception as e:
        print("\n[ERROR] Test failed: {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Analyze specific image
        image_path = sys.argv[1]
        
        try:
            analyzer = VisionAnalyzer()
            analyzer.analyze_and_save(image_path)
        except Exception as e:
            print("[ERROR] Error: {}".format(e))
    else:
        # Run test with latest screenshot
        test_analyzer()
