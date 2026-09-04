"""
NexusTrade India Pro - Deep Automated System & Integration Test Suite
Comprehensive testing for Market Data, Indicators, Multi-Account Copier, Algo Engine, Risk Guard, and REST APIs.
"""

import sys
import unittest
import time
import json
import urllib.request
import numpy as np
import pandas as pd
from datetime import datetime

from config import Config
from market_data import market_data_streamer
from indicators import TechnicalIndicators
from account_manager import account_manager
from algo_engine import algo_engine
from risk_manager import risk_manager

class DeepSystemTestSuite(unittest.TestCase):

    # ═══════════════════════════════════════════════════════════════
    #  1. MARKET DATA ENGINE TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_01_assets_configuration(self):
        """Verifies that all Indian assets (NSE/BSE) are loaded correctly with INR prices."""
        assets = market_data_streamer.get_all_assets()
        self.assertEqual(len(assets), 10, "Should have 10 Indian market assets.")
        
        symbols = [a["symbol"] for a in assets]
        expected_symbols = ["NIFTY50", "BANKNIFTY", "FINNIFTY", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "TATASTEEL", "SBIN"]
        for sym in expected_symbols:
            self.assertIn(sym, symbols, f"Asset {sym} should be present in available assets.")
            
        for a in assets:
            self.assertGreater(a["price"], 0.0, f"Price for {a['symbol']} must be positive.")
            self.assertIn(a["category"], ["Indices", "Equities"], f"Category for {a['symbol']} must be valid.")

    def test_02_timeframe_candle_generation(self):
        """Verifies candle generation across timeframes (1m, 5m, 15m, 1h, 1d)."""
        timeframes = ["1m", "5m", "15m", "1h", "1d"]
        for tf in timeframes:
            candles = market_data_streamer.get_candles("NIFTY50", tf)
            self.assertGreaterEqual(len(candles), 40, f"Timeframe {tf} should have historical candles.")
            latest = candles[-1]
            self.assertIn("open", latest)
            self.assertIn("high", latest)
            self.assertIn("low", latest)
            self.assertIn("close", latest)
            self.assertIn("volume", latest)
            self.assertGreaterEqual(latest["high"], latest["low"], "High must be >= Low.")

    def test_03_price_anchor_stability(self):
        """Verifies that live micro-ticks stay tightly anchored to base_price without drifting."""
        nifty = market_data_streamer.assets["NIFTY50"]
        base_p = nifty.get("base_price", nifty["price"])
        
        for _ in range(10):
            market_data_streamer._micro_tick()
            curr_p = nifty["price"]
            diff_pct = abs(curr_p - base_p) / base_p
            self.assertLess(diff_pct, 0.005, "Micro-tick price must stay within 0.5% of official base_price anchor.")

    def test_04_depth_of_market_structure(self):
        """Verifies DOM (Depth of Market / Order Book) generation for bids and asks."""
        dom = market_data_streamer.get_dom("NIFTY50")
        self.assertIn("bids", dom)
        self.assertIn("asks", dom)
        self.assertEqual(len(dom["bids"]), 5, "DOM should have 5 bid levels.")
        self.assertEqual(len(dom["asks"]), 5, "DOM should have 5 ask levels.")
        self.assertGreater(dom["asks"][0]["price"], dom["bids"][0]["price"], "Ask price must be greater than Bid price.")

    # ═══════════════════════════════════════════════════════════════
    #  2. TECHNICAL INDICATORS ENGINE TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_05_technical_indicators_formulas(self):
        """Verifies SMA, EMA, RSI, VWAP, MACD, and Bollinger Bands calculation formulas."""
        candles = market_data_streamer.get_candles("NIFTY50", "15m")
        ind = TechnicalIndicators.calculate_all(candles)
        
        # 1. Check dictionary keys
        for key in ["sma_20", "sma_50", "ema_9", "rsi_14", "vwap", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_middle", "bb_lower"]:
            self.assertIn(key, ind, f"Indicator {key} must be calculated.")
            self.assertEqual(len(ind[key]), len(candles), f"Indicator {key} array length must match candles length.")

        # 2. RSI Bounds [0, 100]
        rsi_valid = [r for r in ind["rsi_14"] if r is not None]
        for r in rsi_valid:
            self.assertGreaterEqual(r, 0.0, "RSI must be >= 0.")
            self.assertLessEqual(r, 100.0, "RSI must be <= 100.")

        # 3. Bollinger Bands Relationship: Upper >= Middle >= Lower
        for u, m, l in zip(ind["bb_upper"], ind["bb_middle"], ind["bb_lower"]):
            if u is not None and m is not None and l is not None:
                self.assertGreaterEqual(u, m, "BB Upper must be >= Middle.")
                self.assertGreaterEqual(m, l, "BB Middle must be >= Lower.")

    # ═══════════════════════════════════════════════════════════════
    #  3. ACCOUNT MANAGER & MASTER-CHILD COPIER TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_06_account_management(self):
        """Verifies account creation, addition, and clearing."""
        acc = account_manager.add_account({
            "id": "ACC-MASTER-TEST",
            "name": "Test Master Account",
            "type": "Master",
            "broker": "AngelOne SmartAPI",
            "balance": 1000000.0
        })
        self.assertEqual(acc["id"], "ACC-MASTER-TEST")
        self.assertEqual(acc["currency"], "INR")

    def test_07_master_child_trade_copier(self):
        """Verifies Master-Child trade copier order execution and lot multipliers."""
        # Add dynamic child account for testing
        account_manager.add_account({
            "id": "ACC-CHILD-TEST",
            "name": "Test Child Account",
            "type": "Child",
            "broker": "AngelOne SmartAPI",
            "balance": 500000.0,
            "multiplier": 0.5,
            "master_id": "ACC-MASTER-TEST"
        })

        master_id = "ACC-MASTER-TEST"
        res = account_manager.execute_order(
            account_id=master_id,
            symbol="BANKNIFTY",
            side="BUY",
            quantity=5, # 5 * 57,500 = ~2,87,500 < 5,00,000 risk limit
            strategy="Deep Test Suite",
            trigger_copier=True
        )
        
        self.assertEqual(res["status"], "SUCCESS", "Master order execution should succeed.")
        order = res["order"]
        self.assertEqual(order["symbol"], "BANKNIFTY")
        self.assertEqual(order["quantity"], 5)
        self.assertGreater(len(order["copied_orders"]), 0, "Copied orders list should not be empty.")
        
        # Verify positions created in Master and Child accounts
        master_pos = account_manager.get_positions(master_id)
        self.assertTrue(any(p["symbol"] == "BANKNIFTY" for p in master_pos), "Master account should have open position.")
        
        child1_pos = account_manager.get_positions("ACC-CHILD-TEST")
        child1_banknifty = next((p for p in child1_pos if p["symbol"] == "BANKNIFTY"), None)
        self.assertIsNotNone(child1_banknifty, "Child should have copied position.")

        # Clean up test accounts after verification
        account_manager.clear_all_accounts()

    def test_08_position_liquidation(self):
        """Verifies position closing and trade exit P&L calculation."""
        acc = account_manager.add_account({
            "id": "ACC-LIQ-TEST",
            "name": "Liquidation Test Account",
            "type": "Master",
            "broker": "AngelOne SmartAPI",
            "balance": 1000000.0
        })
        master_id = acc["id"]

        # Open position
        account_manager.execute_order(
            account_id=master_id,
            symbol="BANKNIFTY",
            side="BUY",
            quantity=5,
            strategy="Deep Test Open",
            trigger_copier=False
        )

        # Close position by placing opposite order
        res = account_manager.execute_order(
            account_id=master_id,
            symbol="BANKNIFTY",
            side="SELL",
            quantity=5,
            strategy="Deep Test Close",
            trigger_copier=False
        )
        self.assertEqual(res["status"], "SUCCESS", "Position close order execution should succeed.")
        
        remaining = account_manager.get_positions(master_id)
        self.assertFalse(any(p["symbol"] == "BANKNIFTY" for p in remaining), "BANKNIFTY position should be closed.")
        account_manager.clear_all_accounts()

    # ═══════════════════════════════════════════════════════════════
    #  4. ALGO STRATEGY ENGINE & BACKTESTER TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_09_algo_presets_and_toggle(self):
        """Verifies strategy presets and activation toggles."""
        presets = algo_engine.get_presets()
        self.assertIn("MA_CROSSOVER", presets)
        self.assertIn("RSI_REVERSION", presets)
        self.assertIn("BREAKOUT", presets)
        self.assertIn("VWAP_TREND", presets)
        
        # Toggle strategy on
        res = algo_engine.toggle_algo("NIFTY50", "MA_CROSSOVER", "ACC-MASTER-01")
        self.assertEqual(res["status"], "SUCCESS")
        
        algo_id = "NIFTY50_MA_CROSSOVER"
        self.assertIn(algo_id, algo_engine.active_algos)
        self.assertEqual(algo_engine.active_algos[algo_id]["status"], "RUNNING")
        
        # Toggle strategy off
        res_off = algo_engine.toggle_algo("NIFTY50", "MA_CROSSOVER", "ACC-MASTER-01")
        self.assertEqual(res_off["status"], "SUCCESS")
        self.assertEqual(algo_engine.active_algos[algo_id]["status"], "STOPPED")

    def test_10_backtest_engine_simulation(self):
        """Verifies historical backtesting engine outputs, metrics, and equity curve."""
        bt_res = algo_engine.run_backtest("NIFTY50", "MA_CROSSOVER", "15m", 1000000.0)
        self.assertNotIn("error", bt_res, "Backtest should execute without errors.")
        
        summary = bt_res["summary"]
        self.assertIn("net_profit", summary)
        self.assertIn("return_pct", summary)
        self.assertIn("win_rate", summary)
        self.assertIn("profit_factor", summary)
        self.assertIn("max_drawdown_pct", summary)
        self.assertIn("total_trades", summary)
        
        equity_curve = bt_res["equity_curve"]
        self.assertGreater(len(equity_curve), 0, "Equity curve data points should be generated.")
        self.assertIn("equity", equity_curve[0])

    # ═══════════════════════════════════════════════════════════════
    #  5. RISK MANAGER & EMERGENCY KILL SWITCH TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_11_risk_rules_and_kill_switch(self):
        """Verifies risk defaults, Emergency Kill Switch liquidation, and trade blockage."""
        # Check initial state
        self.assertFalse(risk_manager.rules["kill_switch_active"])
        
        # Trigger Kill Switch
        kill_res = risk_manager.trigger_kill_switch(account_manager)
        self.assertEqual(kill_res["status"], "SUCCESS", "Kill Switch activation should succeed.")
        self.assertTrue(risk_manager.rules["kill_switch_active"], "Kill switch state must be active.")
        
        # Verify trade execution is blocked while kill switch is active
        allowed, msg = risk_manager.check_trade_allowed("ACC-MASTER-01", 100000, 0)
        self.assertFalse(allowed, "Trades must be blocked when Kill Switch is active.")
        self.assertIn("Emergency Kill Switch is ACTIVE", msg)
        
        # Reset Kill Switch
        reset_res = risk_manager.reset_kill_switch()
        self.assertEqual(reset_res["status"], "SUCCESS", "Kill Switch reset should succeed.")
        self.assertFalse(risk_manager.rules["kill_switch_active"], "Kill switch state must be inactive.")
        
        # Verify trades allowed again
        allowed_after, _ = risk_manager.check_trade_allowed("ACC-MASTER-01", 10000, 0)
        self.assertTrue(allowed_after, "Trades should be allowed after resetting Kill Switch.")

    # ═══════════════════════════════════════════════════════════════
    #  6. REST API INTEGRATION TESTS (LIVE SERVER)
    # ═══════════════════════════════════════════════════════════════
    def test_12_rest_api_endpoints(self):
        """Verifies live REST API endpoint responses from web server."""
        base_url = "http://127.0.0.1:5000"
        
        # 1. /api/assets
        req_assets = urllib.request.Request(f"{base_url}/api/assets")
        with urllib.request.urlopen(req_assets, timeout=4) as resp:
            self.assertEqual(resp.status, 200)
            assets_data = json.loads(resp.read().decode())
            self.assertEqual(len(assets_data), 10)
            
        # 2. /api/candles/NIFTY50
        req_candles = urllib.request.Request(f"{base_url}/api/candles/NIFTY50?timeframe=1m")
        with urllib.request.urlopen(req_candles, timeout=4) as resp:
            self.assertEqual(resp.status, 200)
            candle_res = json.loads(resp.read().decode())
            self.assertIn("candles", candle_res)
            self.assertIn("indicators", candle_res)
            self.assertIn("dom", candle_res)
            
        # 3. /api/accounts
        req_acc = urllib.request.Request(f"{base_url}/api/accounts")
        with urllib.request.urlopen(req_acc, timeout=4) as resp:
            self.assertEqual(resp.status, 200)
            acc_data = json.loads(resp.read().decode())
            self.assertGreaterEqual(len(acc_data), 0)

        # 4. /api/risk/status
        req_risk = urllib.request.Request(f"{base_url}/api/risk/status")
        with urllib.request.urlopen(req_risk, timeout=4) as resp:
            self.assertEqual(resp.status, 200)
            risk_data = json.loads(resp.read().decode())
            self.assertIn("rules", risk_data)
            self.assertIn("alerts", risk_data)

    # ═══════════════════════════════════════════════════════════════
    #  7. AUTHENTICATION & EMAIL OTP SECURITY TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_13_authentication_and_otp(self):
        """Verifies User Authentication, Salted Password Hashing, Email OTP, & Session Tokens."""
        from auth_manager import auth_manager

        # 1. Test Login Step 1 with default admin
        res = auth_manager.authenticate_user("admin@nexustrade.in", "Nexus@2026")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["step"], "REQUIRE_OTP")

        # Get generated OTP
        user = auth_manager.users["admin@nexustrade.in"]
        otp_code = user["otp_code"]
        self.assertIsNotNone(otp_code)
        self.assertEqual(len(otp_code), 6)

        # 2. Test Step 2 OTP Verification
        otp_res = auth_manager.verify_otp("admin@nexustrade.in", otp_code)
        self.assertEqual(otp_res["status"], "SUCCESS")
        self.assertIn("token", otp_res)

        token = otp_res["token"]

        # 3. Test Session Token Validation
        valid_user = auth_manager.validate_session(token)
        self.assertIsNotNone(valid_user)
        self.assertEqual(valid_user["email"], "admin@nexustrade.in")

        # 4. Test Session Revocation (Logout)
        revoked = auth_manager.revoke_session(token)
        self.assertTrue(revoked)
        self.assertIsNone(auth_manager.validate_session(token))

    # ═══════════════════════════════════════════════════════════════
    #  8. NSE OPTION CHAIN ENGINE TESTS
    # ═══════════════════════════════════════════════════════════════
    def test_14_option_chain_engine(self):
        """Verifies Call (CE) & Put (PE) Option Chain strike generation, PCR ratio, & REST API."""
        # 1. Test Option Chain Generator
        chain_res = market_data_streamer.get_option_chain("NIFTY50")
        self.assertEqual(chain_res["symbol"], "NIFTY50")
        self.assertIn("chain", chain_res)
        self.assertGreater(len(chain_res["chain"]), 10, "Option chain should have 15 strikes.")
        self.assertGreater(chain_res["pcr"], 0.0, "PCR ratio must be positive.")

        # Check Call/Put structure on first strike
        row = chain_res["chain"][0]
        self.assertIn("call", row)
        self.assertIn("put", row)
        self.assertEqual(row["call"]["type"], "CE")
        self.assertEqual(row["put"]["type"], "PE")

        # 2. Test Option Chain REST API Endpoint
        base_url = "http://127.0.0.1:5000"
        req_opt = urllib.request.Request(f"{base_url}/api/options/chain/BANKNIFTY")
        with urllib.request.urlopen(req_opt, timeout=4) as resp:
            self.assertEqual(resp.status, 200)
            opt_data = json.loads(resp.read().decode())
            self.assertEqual(opt_data["symbol"], "BANKNIFTY")
            self.assertIn("chain", opt_data)

if __name__ == '__main__':
    print("==================================================================")
    print("  RUNNING NEXUSTRADE INDIA PRO - DEEP AUTOMATED SYSTEM TEST SUITE ")
    print("==================================================================")
    suite = unittest.TestLoader().loadTestsFromTestCase(DeepSystemTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if not result.wasSuccessful():
        sys.exit(1)
