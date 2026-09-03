"""
Antigravity AlgoTrader Pro - Comprehensive System Verification Suite
"""

import sys
import unittest
import numpy as np
import pandas as pd

from config import Config
from market_data import market_data_streamer
from indicators import TechnicalIndicators
from account_manager import account_manager
from algo_engine import algo_engine
from risk_manager import risk_manager

class TestTradingPlatform(unittest.TestCase):

    def test_01_market_data(self):
        """Verifies candle generation and tick streamer."""
        assets = market_data_streamer.get_all_assets()
        self.assertGreater(len(assets), 0, "Assets list should not be empty.")
        
        candles = market_data_streamer.get_candles("NIFTY50", "1m")
        self.assertGreaterEqual(len(candles), 100, "Historical candles should be generated.")
        
        latest = candles[-1]
        self.assertIn("open", latest)
        self.assertIn("high", latest)
        self.assertIn("low", latest)
        self.assertIn("close", latest)

    def test_02_indicators(self):
        """Verifies technical indicator calculations."""
        candles = market_data_streamer.get_candles("NIFTY50", "15m")
        ind = TechnicalIndicators.calculate_all(candles)
        
        self.assertIn("sma_20", ind)
        self.assertIn("rsi_14", ind)
        self.assertIn("macd", ind)
        self.assertIn("vwap", ind)
        self.assertEqual(len(ind["rsi_14"]), len(candles))

    def test_03_multi_account_copy_trading(self):
        """Verifies Master-Child trade copier execution."""
        accounts = account_manager.get_all_accounts()
        master = next(a for a in accounts if a["type"] == "Master")
        child_1 = next(a for a in accounts if a["id"] == "ACC-CHILD-01")
        
        # Execute Buy on Master
        res = account_manager.execute_order(
            account_id=master["id"],
            symbol="NIFTY50",
            side="BUY",
            quantity=1,
            strategy="Unit Test Copy Trade",
            trigger_copier=True
        )
        
        self.assertEqual(res["status"], "SUCCESS")
        order = res["order"]
        self.assertGreater(len(order["copied_orders"]), 0, "Master order should copy trades to child accounts.")

    def test_04_backtester(self):
        """Verifies strategy backtesting engine output."""
        res = algo_engine.run_backtest("NIFTY50", "MA_CROSSOVER", "15m", 100000.0)
        self.assertNotIn("error", res)
        summary = res["summary"]
        self.assertIn("net_profit", summary)
        self.assertIn("win_rate", summary)
        self.assertIn("max_drawdown_pct", summary)

    def test_05_risk_manager_kill_switch(self):
        """Verifies Emergency Kill Switch liquidation."""
        res = risk_manager.trigger_kill_switch(account_manager)
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(risk_manager.rules["kill_switch_active"])
        
        # Verify new trades are blocked when kill switch is active
        allowed, msg = risk_manager.check_trade_allowed("ACC-MASTER-01", 10000, 0)
        self.assertFalse(allowed)
        
        # Reset kill switch
        risk_manager.reset_kill_switch()
        self.assertFalse(risk_manager.rules["kill_switch_active"])

if __name__ == '__main__':
    print("============================================================")
    print("   RUNNING ANTIGRAVITY ALGOTRADER PRO VERIFICATION TESTS    ")
    print("============================================================")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTradingPlatform)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)
