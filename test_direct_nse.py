import subprocess
import json
import os
import time

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "scratch", "nse_session.txt")
os.makedirs(os.path.dirname(COOKIE_FILE), exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

def refresh_nse_cookies():
    cmd = [
        "curl.exe", "-s", "-L",
        "-c", COOKIE_FILE,
        "-H", f"User-Agent: {USER_AGENT}",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: en-US,en;q=0.9",
        "https://www.nseindia.com"
    ]
    subprocess.run(cmd, capture_output=True)

def fetch_nse_endpoint(endpoint):
    cmd = [
        "curl.exe", "-s", "-L",
        "-b", COOKIE_FILE,
        "-c", COOKIE_FILE,
        "-H", f"User-Agent: {USER_AGENT}",
        "-H", "Accept: application/json, text/plain, */*",
        "-H", "Referer: https://www.nseindia.com/",
        f"https://www.nseindia.com{endpoint}"
    ]
    proc = subprocess.run(cmd, capture_output=True)
    out = proc.stdout.decode('utf-8', errors='ignore')
    try:
        return json.loads(out)
    except Exception:
        return None

def get_official_nse_live_data():
    refresh_nse_cookies()
    time.sleep(1)
    
    # 1. Fetch All Indices directly from www.nseindia.com/api/allIndices
    indices_data = fetch_nse_endpoint("/api/allIndices")
    if indices_data and 'data' in indices_data:
        print("DIRECT NSE API - INDICES FETCHED SUCCESSFULLY!")
        index_map = {
            "NIFTY 50": "NIFTY50",
            "NIFTY BANK": "BANKNIFTY",
            "NIFTY FINANCIAL SERVICES": "FINNIFTY"
        }
        for item in indices_data['data']:
            name = item.get('index')
            if name in index_map:
                sym = index_map[name]
                last = item.get('last')
                chg = item.get('percentChange')
                print(f"  [NSE DIRECT INDEX] {sym} ({name}): price={last}, change={chg}%")

    # 2. Fetch NIFTY 50 Equities directly from www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050
    equity_data = fetch_nse_endpoint("/api/equity-stockIndices?index=NIFTY%2050")
    if equity_data and 'data' in equity_data:
        print("\nDIRECT NSE API - EQUITIES FETCHED SUCCESSFULLY!")
        for item in equity_data['data'][:8]:
            sym = item.get('symbol')
            price = item.get('lastPrice')
            chg = item.get('pChange')
            print(f"  [NSE DIRECT EQUITY] {sym}: price={price}, change={chg}%")

if __name__ == '__main__':
    get_official_nse_live_data()
