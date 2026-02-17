import MetaTrader5 as mt5

mt5.shutdown()

if not mt5.initialize():
    print(f"MT5 init failed: {mt5.last_error()}")
else:
    print(f"MT5 connected: {mt5.terminal_info()}")
    print(f"Account: {mt5.account_info()}")
    mt5.shutdown()
