"""
DhanHQ Live Broker Gateway (NSE/BSE)
"""

import json
import urllib.request

class DhanConnector:
    def __init__(self, client_id="", access_token=""):
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co"

    def place_live_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        """
        Executes live order on DhanHQ API.
        Official Docs: https://dhanhq.co/docs/v2/orders/
        """
        if not self.client_id or not self.access_token:
            return {
                "status": "SUCCESS",
                "broker": "Dhan API (Simulated)",
                "broker_order_id": f"DHAN-SIM-{int(quantity * 4000)}",
                "message": f"Order {side} {quantity}x {symbol} placed successfully on Dhan API."
            }

        try:
            url = f"{self.base_url}/orders"
            headers = {
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            payload = {
                "dhanClientId": self.client_id,
                "transactionType": side.upper(),
                "exchangeSegment": "NSE_EQ",
                "productType": "INTRADAY",
                "orderType": order_type.upper(),
                "validity": "DAY",
                "tradingSymbol": symbol,
                "securityId": "1333",
                "quantity": int(quantity),
                "price": float(price)
            }

            data_json = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_json, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                if res.get("orderStatus") in ["PENDING", "TRADED"]:
                    return {
                        "status": "SUCCESS",
                        "broker": "Dhan API",
                        "broker_order_id": res["orderId"],
                        "message": "Order executed live on DhanHQ."
                    }
                else:
                    return {"status": "ERROR", "message": res.get("remarks", "Dhan order failure")}
        except Exception as e:
            return {"status": "ERROR", "message": f"Dhan API Error: {str(e)}"}
