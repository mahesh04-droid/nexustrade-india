"""
Antigravity AlgoTrader Pro - Risk Management Guard & Emergency Kill Switch Engine
"""

from config import Config

class RiskManager:
    def __init__(self):
        self.rules = dict(Config.RISK_DEFAULTS)
        self.daily_pnl = 0.0
        self.alerts = []

    def update_rules(self, new_rules):
        """Updates risk parameter settings."""
        self.rules.update(new_rules)
        self._add_alert("INFO", f"Risk rules updated: Max Loss=${self.rules['max_daily_loss']}, SL={self.rules['default_stop_loss_pct']}%, TP={self.rules['default_take_profit_pct']}%")
        return self.rules

    def check_trade_allowed(self, account_id, position_size, current_daily_loss):
        """Checks if a new trade violates risk parameters."""
        if self.rules.get("kill_switch_active", False):
            return False, "Emergency Kill Switch is ACTIVE. No trades allowed."
            
        if abs(current_daily_loss) >= self.rules["max_daily_loss"]:
            return False, f"Max Daily Loss Limit (${self.rules['max_daily_loss']}) breached. Circuit breaker active."
            
        if position_size > self.rules["max_position_size"]:
            return False, f"Position size (${position_size}) exceeds maximum allowed limit (${self.rules['max_position_size']})."
            
        return True, "Trade permitted."

    def trigger_kill_switch(self, account_manager):
        """Activates emergency kill switch and liquidates all open positions across all accounts."""
        self.rules["kill_switch_active"] = True
        liquidated_count = account_manager.liquidate_all_positions()
        
        msg = f"EMERGENCY KILL SWITCH TRIGGERED! Liquidated {liquidated_count} positions across all accounts."
        self._add_alert("CRITICAL", msg)
        return {"status": "SUCCESS", "message": msg, "liquidated_positions": liquidated_count}

    def reset_kill_switch(self):
        """Resets the kill switch allowing trading to resume."""
        self.rules["kill_switch_active"] = False
        self._add_alert("WARNING", "Kill Switch reset by operator. Trading allowed.")
        return {"status": "SUCCESS", "message": "Kill switch deactivated."}

    def _add_alert(self, level, text):
        from datetime import datetime
        self.alerts.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level, # "INFO", "WARNING", "CRITICAL"
            "text": text
        })
        # Keep last 50 alerts
        self.alerts = self.alerts[:50]

    def get_status(self):
        return {
            "rules": self.rules,
            "alerts": self.alerts
        }

# Global risk manager instance
risk_manager = RiskManager()
