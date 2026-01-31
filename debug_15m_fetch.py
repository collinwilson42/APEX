# debug_15m_fetch.py - Check if MT5 returns 15m data
import MetaTrader5 as mt5

mt5.initialize()

symbol = "XAUJ26.sim"

# Check 1m
rates_1m = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 50000)
print(f"1m bars available: {len(rates_1m) if rates_1m is not None else 0}")

# Check 15m
rates_15m = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50000)
print(f"15m bars available: {len(rates_15m) if rates_15m is not None else 0}")

mt5.shutdown()
