"""
NexusTrade India - Configuration Module (NSE/BSE Indian Markets & INR Currency)
"""

import os

class Config:
    # Server Settings
    HOST = '127.0.0.1'
    PORT = 5000
    DEBUG = True

    # Initial Accounts Setup (Indian Paper Trading Defaults in INR)
    INITIAL_ACCOUNTS = [
        {
            "id": "ACC-MASTER-01",
            "name": "Master Account (Zerodha Kite)",
            "type": "Master",
            "broker": "Zerodha Kite Connect (NSE/BSE)",
            "balance": 1000000.00, # ₹10 Lakhs
            "currency": "INR",
            "status": "Connected",
            "mode": "Paper", # "Paper" or "Live"
            "api_key": "kite_live_master_sec_xxxx",
            "api_secret": "••••••••••••••••",
            "copied_by": ["ACC-CHILD-01", "ACC-CHILD-02"]
        },
        {
            "id": "ACC-CHILD-01",
            "name": "Child Account 1 (AngelOne)",
            "type": "Child",
            "broker": "AngelOne SmartAPI (NSE/BSE)",
            "balance": 500000.00, # ₹5 Lakhs
            "currency": "INR",
            "status": "Connected",
            "mode": "Paper",
            "api_key": "angel_child1_sec_yyyy",
            "api_secret": "••••••••••••••••",
            "multiplier": 0.5, # Copy 50% lot size of master
            "master_id": "ACC-MASTER-01"
        },
        {
            "id": "ACC-CHILD-02",
            "name": "Child Account 2 (Upstox)",
            "type": "Child",
            "broker": "Upstox API (NSE/BSE)",
            "balance": 2500000.00, # ₹25 Lakhs
            "currency": "INR",
            "status": "Connected",
            "mode": "Paper",
            "api_key": "upstox_child2_sec_zzzz",
            "api_secret": "••••••••••••••••",
            "multiplier": 2.0, # Copy 200% lot size of master
            "master_id": "ACC-MASTER-01"
        }
    ]

    # Global Risk Defaults (in INR)
    RISK_DEFAULTS = {
        "max_daily_loss": 25000.0,      # ₹25,000 Daily Loss Circuit Breaker
        "max_position_size": 500000.0,  # ₹5,00,000 Max Position Limit
        "default_stop_loss_pct": 1.5,   # 1.5% SL
        "default_take_profit_pct": 3.0, # 3.0% TP
        "trailing_stop_enabled": True,
        "trailing_stop_pct": 1.0,
        "kill_switch_active": False
    }

    # Indian Market Assets (NSE/BSE Equities, F&O, Indices)
    AVAILABLE_ASSETS = [
        {"symbol": "NIFTY50", "name": "Nifty 50 Index Futures", "price": 23914.40, "category": "Indices", "decimals": 2},
        {"symbol": "BANKNIFTY", "name": "Bank Nifty Index Futures", "price": 57172.00, "category": "Indices", "decimals": 2},
        {"symbol": "FINNIFTY", "name": "Nifty Financial Services", "price": 24250.00, "category": "Indices", "decimals": 2},
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "price": 1285.50, "category": "Equities", "decimals": 2},
        {"symbol": "TCS", "name": "Tata Consultancy Services", "price": 4120.00, "category": "Equities", "decimals": 2},
        {"symbol": "INFY", "name": "Infosys Limited", "price": 1895.00, "category": "Equities", "decimals": 2},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Limited", "price": 1740.00, "category": "Equities", "decimals": 2},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Limited", "price": 1260.00, "category": "Equities", "decimals": 2},
        {"symbol": "TATAMOTORS", "name": "Tata Motors Limited", "price": 780.00, "category": "Equities", "decimals": 2},
        {"symbol": "SBIN", "name": "State Bank of India", "price": 845.00, "category": "Equities", "decimals": 2}
    ]
