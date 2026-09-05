"""
Antigravity AlgoTrader Pro - Main Server & API Router
"""

import json
import os
import sys
import threading
import time
from bottle import Bottle, request, response, static_file, run

from config import Config
from market_data import market_data_streamer
from indicators import TechnicalIndicators
from account_manager import account_manager
from algo_engine import algo_engine
from risk_manager import risk_manager
from auth_manager import auth_manager

app = Bottle()

# Utility JSON helper
def json_resp(data, status=200):
    response.content_type = 'application/json'
    response.status = status
    return json.dumps(data)

# Helper to validate active user session (Temporarily bypassed for testing mode)
def get_current_user():
    # Bypass auth for testing: Return admin user directly
    return {"email": "admin@nexustrade.in", "name": "Platform Administrator"}

# Static Files & Login Page
@app.route('/')
def index():
    return static_file('index.html', root=os.path.join(os.path.dirname(__file__), 'static'))

@app.route('/login')
def login_page():
    return static_file('login.html', root=os.path.join(os.path.dirname(__file__), 'static'))

@app.route('/static/<filepath:path>')
def server_static(filepath):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return static_file(filepath, root=os.path.join(os.path.dirname(__file__), 'static'))

# API - Security & Authentication Routes
@app.route('/api/auth/login', method='POST')
def auth_login():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        email = data.get("email", "")
        password = data.get("password", "")
        res = auth_manager.authenticate_user(email, password)
        return json_resp(res, 200 if res["status"] == "SUCCESS" else 401)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/auth/verify-otp', method='POST')
def auth_verify_otp():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        email = data.get("email", "")
        otp_code = data.get("otp_code", "")
        res = auth_manager.verify_otp(email, otp_code)
        if res["status"] == "SUCCESS":
            response.set_cookie("nexus_token", res["token"], path="/", max_age=86400*7)
        return json_resp(res, 200 if res["status"] == "SUCCESS" else 401)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/auth/logout', method='POST')
def auth_logout():
    token = request.get_header('X-Auth-Token') or request.cookies.get('nexus_token')
    auth_manager.revoke_session(token)
    response.delete_cookie("nexus_token", path="/")
    return json_resp({"status": "SUCCESS", "message": "Logged out successfully."})

@app.route('/api/auth/me', method='GET')
def auth_me():
    user = get_current_user()
    if user:
        return json_resp({"authenticated": True, "user": {"email": user["email"], "name": user["name"]}})
    return json_resp({"authenticated": False}, 401)

# API - Market Data & Indicators
@app.route('/api/market/mode', method='GET')
def get_market_mode():
    return json_resp({"mode": market_data_streamer.mode})

@app.route('/api/market/mode', method='POST')
def set_market_mode():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        mode = data.get("mode", "LIVE")
        success, msg = market_data_streamer.set_mode(mode)
        return json_resp({"status": "SUCCESS" if success else "ERROR", "message": msg, "mode": market_data_streamer.mode})
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/assets', method='GET')
def get_assets():
    return json_resp(market_data_streamer.get_all_assets())

@app.route('/api/candles/<symbol>', method='GET')
def get_candles(symbol):
    tf = request.query.get('timeframe', '1m')
    candles = market_data_streamer.get_candles(symbol, tf)
    indicators = TechnicalIndicators.calculate_all(candles)
    dom = market_data_streamer.get_dom(symbol)
    
    return json_resp({
        "symbol": symbol,
        "timeframe": tf,
        "candles": candles,
        "indicators": indicators,
        "dom": dom
    })

@app.route('/api/options/chain/<symbol>', method='GET')
def get_option_chain(symbol):
    exp = request.query.get('expiry', None)
    return json_resp(market_data_streamer.get_option_chain(symbol, exp))

# API - Accounts & Master-Child Copier
@app.route('/api/accounts', method='GET')
def get_accounts():
    return json_resp(account_manager.get_all_accounts())

@app.route('/api/accounts', method='POST')
def add_account():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        acc = account_manager.add_account(data)
        return json_resp({"status": "SUCCESS", "account": acc})
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/accounts/<acc_id>', method='PUT')
def update_account(acc_id):
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        acc = account_manager.update_account(acc_id, data)
        return json_resp({"status": "SUCCESS", "account": acc})
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/accounts/clear', method='POST')
@app.route('/api/accounts/all', method='DELETE')
def clear_all_accounts():
    try:
        account_manager.clear_all_accounts()
        return json_resp({"status": "SUCCESS", "message": "All account profiles cleared."})
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 500)

@app.route('/api/accounts/<acc_id>', method='DELETE')
def delete_account(acc_id):
    try:
        success = account_manager.delete_account(acc_id)
        if success:
            return json_resp({"status": "SUCCESS", "message": f"Account {acc_id} deleted."})
        return json_resp({"status": "ERROR", "message": "Account not found."}, 44)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/accounts/<acc_id>/sync', method='POST')
def sync_account_balance(acc_id):
    try:
        res = account_manager.sync_broker_balance(acc_id)
        return json_resp(res)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 500)

# API - Order Placement & Execution
@app.route('/api/orders/place', method='POST')
def place_order():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        acc_id = data.get("account_id", "ACC-MASTER-01")
        symbol = data.get("symbol", "NIFTY50")
        side = data.get("side", "BUY")
        qty = int(data.get("quantity", 1))
        order_type = data.get("type", "MARKET")
        strategy = data.get("strategy", "Manual Terminal")
        
        res = account_manager.execute_order(
            account_id=acc_id,
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type=order_type,
            strategy=strategy,
            trigger_copier=True
        )
        return json_resp(res, 200 if res.get("status") == "SUCCESS" else 400)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 500)

@app.route('/api/orders/history', method='GET')
def get_order_history():
    return json_resp(account_manager.get_order_history(100))

# API - Algo Strategies & Backtester
@app.route('/api/algo/presets', method='GET')
def get_algo_presets():
    return json_resp({
        "presets": algo_engine.get_presets(),
        "active_algos": algo_engine.active_algos
    })

@app.route('/api/algo/toggle', method='POST')
def toggle_algo():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        symbol = data.get("symbol")
        strategy_key = data.get("strategy_key")
        account_id = data.get("account_id", "ACC-MASTER-01")
        params = data.get("params")
        
        res = algo_engine.toggle_algo(symbol, strategy_key, account_id, params)
        return json_resp(res)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/algo/backtest', method='POST')
def run_backtest():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        symbol = data.get("symbol", "NIFTY50")
        strategy_key = data.get("strategy_key", "MA_CROSSOVER")
        timeframe = data.get("timeframe", "15m")
        capital = float(data.get("initial_capital", 1000000.0))
        params = data.get("params")
        
        res = algo_engine.run_backtest(symbol, strategy_key, timeframe, capital, params)
        return json_resp(res)
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 500)

# API - 1-Click Interactive Live Demo Setup
@app.route('/api/demo/setup', method='POST')
def setup_demo_environment():
    try:
        # 1. Place a sample live trade on Master Account
        order_res = account_manager.execute_order(
            account_id="ACC-MASTER-01",
            symbol="NIFTY50",
            side="BUY",
            quantity=5,
            strategy="1-Click Demo Showcase",
            trigger_copier=True
        )
        # 2. Activate VWAP Trend automated strategy
        algo_res = algo_engine.toggle_algo("NIFTY50", "VWAP_TREND", "ACC-MASTER-01")
        
        return json_resp({
            "status": "SUCCESS",
            "message": "Live Interactive Demo environment loaded! Order placed & VWAP Trend Algo activated.",
            "order": order_res.get("order"),
            "algo": algo_res
        })
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 500)

# API - Risk Manager & Emergency Kill Switch
@app.route('/api/risk/status', method='GET')
def get_risk_status():
    return json_resp(risk_manager.get_status())

@app.route('/api/risk/update', method='POST')
def update_risk_rules():
    try:
        data = request.json or json.loads(request.body.read().decode('utf-8'))
        updated = risk_manager.update_rules(data)
        return json_resp({"status": "SUCCESS", "rules": updated})
    except Exception as e:
        return json_resp({"status": "ERROR", "message": str(e)}, 400)

@app.route('/api/risk/kill-switch', method='POST')
def trigger_kill_switch():
    res = risk_manager.trigger_kill_switch(account_manager)
    return json_resp(res)

@app.route('/api/risk/kill-switch/reset', method='POST')
def reset_kill_switch():
    res = risk_manager.reset_kill_switch()
    return json_resp(res)

# Background tick simulator thread
def tick_worker():
    while True:
        try:
            market_data_streamer.update_tick()
            algo_engine.process_live_tick()
            time.sleep(1.0) # Tick every second
        except Exception as e:
            time.sleep(1.0)

# Launch background thread
tick_thread = threading.Thread(target=tick_worker, daemon=True)
tick_thread.start()

def launch_app():
    print(f"============================================================")
    print(f"  ANTIGRAVITY ALGOTRADER PRO - SERVER RUNNING")
    print(f"  Access UI at: http://{Config.HOST}:{Config.PORT}")
    print(f"============================================================")
    
    # Try launching PyWebView if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--desktop':
        try:
            import webview
            server_thread = threading.Thread(target=lambda: run(app, host=Config.HOST, port=Config.PORT, quiet=True), daemon=True)
            server_thread.start()
            time.sleep(1.2)
            webview.create_window('Antigravity AlgoTrader Pro', f'http://{Config.HOST}:{Config.PORT}', width=1400, height=900)
            webview.start()
            return
        except Exception as e:
            print(f"PyWebView launch warning: {e}. Falling back to web server mode.")
            
    port = int(os.environ.get('PORT', Config.PORT))
    host = '0.0.0.0' if 'PORT' in os.environ else Config.HOST
    run(app, host=host, port=port, debug=Config.DEBUG)

if __name__ == '__main__':
    launch_app()
