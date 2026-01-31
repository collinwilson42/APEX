# test_mt5_rates.py - Check what MT5 returns
import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()

rates = mt5.copy_rates_from_pos("XAUJ26.sim", mt5.TIMEFRAME_M1, 0, 5)

print(f"Type: {type(rates)}")
print(f"Dtype: {rates.dtype if hasattr(rates, 'dtype') else 'N/A'}")
print(f"\nFirst rate:")
print(f"  Full: {rates[0]}")
print(f"  Type: {type(rates[0])}")

# Test different access methods
print(f"\nAccess methods:")
try:
    print(f"  rates[0]['close'] = {rates[0]['close']}")
except Exception as e:
    print(f"  rates[0]['close'] FAILED: {e}")

try:
    print(f"  rates[0][4] = {rates[0][4]}")  # close is index 4
except Exception as e:
    print(f"  rates[0][4] FAILED: {e}")

mt5.shutdown()
