"""
Antigravity AlgoTrader Pro - Multi-Account Management & Master-Child Trade Copier Engine
"""

import uuid
from datetime import datetime, timedelta
from config import Config
from market_data import market_data_streamer

class AccountManager:
    def __init__(self):
        self.accounts = {acc["id"]: dict(acc) for acc in Config.INITIAL_ACCOUNTS}
        self.positions = {} # acc_id -> list of position dicts
        self.order_history = []
        
        # Initialize position structures
        for acc_id in self.accounts:
            self.positions[acc_id] = []
            
        # Seed initial sample trades for demonstration analytics
        self._seed_sample_orders()

    def _seed_sample_orders(self):
        """Seeds realistic historical execution logs for immediate visual feedback."""
        sample_assets = ["NIFTY50", "BANKNIFTY", "RELIANCE", "TCS", "HDFCBANK", "INFY"]
        now = datetime.now()
        
        for i in range(12):
            asset = sample_assets[i % len(sample_assets)]
            info = market_data_streamer.get_asset_info(asset)
            price = info["price"] if info else 1000.0
            qty = (i + 1) * 5
            side = "BUY" if i % 2 == 0 else "SELL"
            pnl = round((i * 450.5) - 300.0, 2)
            
            self.order_history.append({
                "order_id": f"ORD-{1000 + i}",
                "account_id": "ACC-MASTER-01",
                "account_name": "Master Account (Zerodha Kite)",
                "symbol": asset,
                "side": side,
                "quantity": qty,
                "price": price,
                "status": "FILLED",
                "type": "MARKET",
                "strategy": "MA Crossover" if i % 2 == 0 else "Manual Terminal",
                "copied_orders": [f"ORD-{2000 + i}", f"ORD-{3000 + i}"],
                "realized_pnl": pnl,
                "timestamp": (now - timedelta(hours=i*2)).strftime("%Y-%m-%d %H:%M:%S")
            })

    def get_all_accounts(self):
        """Returns account summaries including balance, P&L, and open positions."""
        result = []
        for acc_id, acc in self.accounts.items():
            acc_copy = dict(acc)
            acc_positions = self.positions.get(acc_id, [])
            
            # Compute live unrealized P&L
            unrealized_pnl = 0.0
            for pos in acc_positions:
                curr_price = market_data_streamer.assets.get(pos["symbol"], {}).get("price", pos["entry_price"])
                if pos["side"] == "BUY":
                    pos["pnl"] = round((curr_price - pos["entry_price"]) * pos["quantity"], 2)
                else:
                    pos["pnl"] = round((pos["entry_price"] - curr_price) * pos["quantity"], 2)
                unrealized_pnl += pos["pnl"]
                
            acc_copy["unrealized_pnl"] = round(unrealized_pnl, 2)
            acc_copy["open_positions_count"] = len(acc_positions)
            acc_copy["total_equity"] = round(acc["balance"] + unrealized_pnl, 2)
            result.append(acc_copy)
        return result

    def add_account(self, account_data):
        """Adds or connects a new broker account profile."""
        acc_id = account_data.get("id") or f"ACC-{uuid.uuid4().hex[:6].upper()}"
        new_acc = {
            "id": acc_id,
            "name": account_data.get("name", "New Account"),
            "type": account_data.get("type", "Child"), # "Master" or "Child"
            "broker": account_data.get("broker", "Paper Simulator"),
            "balance": float(account_data.get("balance", 500000.0)),
            "currency": account_data.get("currency", "INR"),
            "status": "Connected",
            "mode": account_data.get("mode", "Paper"),
            "api_key": account_data.get("api_key", "sec_xxxx"),
            "api_secret": "••••••••••••••••",
            "multiplier": float(account_data.get("multiplier", 1.0)),
            "master_id": account_data.get("master_id", "ACC-MASTER-01")
        }
        self.accounts[acc_id] = new_acc
        self.positions[acc_id] = []
        return new_acc

    def update_account(self, acc_id, updates):
        """Updates account settings or broker API credentials."""
        if acc_id in self.accounts:
            self.accounts[acc_id].update(updates)
            return self.accounts[acc_id]
        return None

    def execute_order(self, account_id, symbol, side, quantity, order_type="MARKET", strategy="Manual Terminal", trigger_copier=True):
        """
        Executes an order on an account. 
        If account is Master and trigger_copier=True, automatically copies the order to linked Child accounts.
        """
        from risk_manager import risk_manager
        
        acc = self.accounts.get(account_id)
        if not acc:
            return {"status": "ERROR", "message": f"Account {account_id} not found."}
            
        asset_info = market_data_streamer.get_asset_info(symbol)
        if not asset_info:
            return {"status": "ERROR", "message": f"Asset {symbol} invalid."}
            
        price = asset_info["price"]
        order_cost = price * quantity
        
        # Risk check
        curr_loss = sum(o.get("realized_pnl", 0) for o in self.order_history if o.get("account_id") == account_id and o.get("realized_pnl", 0) < 0)
        allowed, risk_msg = risk_manager.check_trade_allowed(account_id, order_cost, curr_loss)
        if not allowed:
            return {"status": "ERROR", "message": risk_msg}
            
        # Create Master order
        order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
        copied_order_ids = []
        
        # Multi-Account Trade Copier Engine
        if trigger_copier and acc["type"] == "Master":
            for child_id, child_acc in self.accounts.items():
                if child_acc.get("master_id") == account_id and child_acc.get("type") == "Child":
                    child_multiplier = child_acc.get("multiplier", 1.0)
                    child_qty = max(1, round(quantity * child_multiplier))
                    
                    # Execute mirrored trade on child account
                    child_res = self.execute_order(
                        account_id=child_id,
                        symbol=symbol,
                        side=side,
                        quantity=child_qty,
                        order_type=order_type,
                        strategy=f"Copied from Master ({strategy})",
                        trigger_copier=False # Prevent recursive copies
                    )
                    if child_res.get("status") == "SUCCESS":
                        copied_order_ids.append(child_res["order"]["order_id"])

        # Update position on target account
        self._apply_position_change(account_id, symbol, side, quantity, price)

        order_record = {
            "order_id": order_id,
            "account_id": account_id,
            "account_name": acc["name"],
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "status": "FILLED",
            "type": order_type,
            "strategy": strategy,
            "copied_orders": copied_order_ids,
            "realized_pnl": 0.0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.order_history.insert(0, order_record)
        return {"status": "SUCCESS", "message": f"{side} order executed for {symbol} on {acc['name']}.", "order": order_record}

    def _apply_position_change(self, account_id, symbol, side, quantity, price):
        """Updates open positions array for an account."""
        positions = self.positions.get(account_id, [])
        existing = next((p for p in positions if p["symbol"] == symbol), None)
        
        if not existing:
            # Create new open position
            positions.append({
                "pos_id": f"POS-{uuid.uuid4().hex[:4].upper()}",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "entry_price": price,
                "current_price": price,
                "pnl": 0.0,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            if existing["side"] == side:
                # Add to existing position (average price)
                tot_qty = existing["quantity"] + quantity
                existing["entry_price"] = round(((existing["entry_price"] * existing["quantity"]) + (price * quantity)) / tot_qty, 2)
                existing["quantity"] = tot_qty
            else:
                # Reduce or close position
                if quantity >= existing["quantity"]:
                    # Closed completely
                    positions.remove(existing)
                else:
                    existing["quantity"] -= quantity

    def liquidate_all_positions(self):
        """Liquidates all open positions across all accounts immediately."""
        total_closed = 0
        for acc_id, pos_list in list(self.positions.items()):
            for pos in list(pos_list):
                opp_side = "SELL" if pos["side"] == "BUY" else "BUY"
                self.execute_order(
                    account_id=acc_id,
                    symbol=pos["symbol"],
                    side=opp_side,
                    quantity=pos["quantity"],
                    strategy="Emergency Liquidation",
                    trigger_copier=False
                )
                total_closed += 1
            self.positions[acc_id] = []
        return total_closed

    def get_positions(self, account_id=None):
        """Returns open positions for account or all accounts."""
        if account_id:
            return self.positions.get(account_id, [])
        return self.positions

    def get_order_history(self, limit=50):
        return self.order_history[:limit]

# Global account manager instance
account_manager = AccountManager()
