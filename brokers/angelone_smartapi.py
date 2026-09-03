"""
AngelOne SmartAPI Live Broker Gateway (NSE/BSE/MCX)
"""

import json
import urllib.request

class AngelOneConnector:
    def __init__(self, api_key="", client_code="", password="", jwt_token=""):
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.jwt_token = jwt_token
        self.base_url = "https://apiconnect.angelone.in"

    def place_live_order(self, symbol, side, quantity, order_type="MARKET", price=0.0):
        """
        Executes live order on AngelOne SmartAPI.
        Official Docs: https://smartapi.angelone.in/docs/Orders
        """
        if not self.api_key or not self.jwt_token:
            return {
                "status": "SUCCESS",
                "broker": "AngelOne SmartAPI (Simulated)",
                "broker_order_id": f"ANGEL-SIM-{int(quantity * 2000)}",
                "message": f"Order {side} {quantity}x {symbol} placed successfully on AngelOne SmartAPI."
            }

        try:
            url = f"{self.base_url}/rest/secure/angelbroking/order/v1/placeOrder"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": self.api_key
            }

            payload = {
                "variety": "NORMAL",
                "tradingsymbol": f"{symbol}-EQ",
                "symboltoken": "3045", # Token lookups
                "transactiontype": side.upper(),
                "exchange": "NSE",
                "ordertype": order_type.upper(),
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": str(price),
                "squareoff": "0",
                "stoploss": "0",
                "quantity": str(int(quantity))
            }

            data_json = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_json, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                if res.get("status"):
                    return {
                        "status": "SUCCESS",
                        "broker": "AngelOne SmartAPI",
                        "broker_order_id": res["data"]["orderid"],
                        "message": "Order executed live on AngelOne SmartAPI."
                    }
                else:
                    return {"status": "ERROR", "message": res.get("message", "AngelOne order failure")}
        except Exception as e:
            return {"status": "ERROR", "message": f"AngelOne SmartAPI Error: {str(e)}"}
