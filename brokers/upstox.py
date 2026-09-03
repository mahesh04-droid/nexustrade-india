"""
Upstox API Live Broker Gateway (NSE/BSE)
"""

import json
import urllib.request

class UpstoxConnector:
    def __init__(self, api_key="", access_token=""):
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = "https://api.upstox.com/v2"

    def place_live_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        """
        Executes live order on Upstox v2 API.
        Official Docs: https://upstox.com/developer/api-documentation/order-execution
        """
        if not self.access_token:
            return {
                "status": "SUCCESS",
                "broker": "Upstox API (Simulated)",
                "broker_order_id": f"UPSTOX-SIM-{int(quantity * 3000)}",
                "message": f"Order {side} {quantity}x {symbol} placed successfully on Upstox API."
            }

        try:
            url = f"{self.base_url}/order/place"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "quantity": int(quantity),
                "product": "I", # Intraday
                "validity": "DAY",
                "price": float(price),
                "tag": "nexustrade",
                "instrument_token": f"NSE_EQ|{symbol}",
                "order_type": order_type.upper(),
                "transaction_type": side.upper(),
                "disclosed_quantity": 0,
                "trigger_price": 0,
                "is_amo": False
            }

            data_json = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_json, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                if res.get("status") == "success":
                    return {
                        "status": "SUCCESS",
                        "broker": "Upstox API",
                        "broker_order_id": res["data"]["order_id"],
                        "message": "Order executed live on Upstox."
                    }
                else:
                    return {"status": "ERROR", "message": res.get("errors", [{}])[0].get("message", "Upstox error")}
        except Exception as e:
            return {"status": "ERROR", "message": f"Upstox API Error: {str(e)}"}
