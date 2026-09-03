"""
Antigravity AlgoTrader Pro - Algorithmic Strategy Engine & Backtest Simulator
"""

import numpy as np
import pandas as pd
from datetime import datetime
from indicators import TechnicalIndicators
from market_data import market_data_streamer
from account_manager import account_manager

class StrategyPresets:
    STRATEGIES = {
        "MA_CROSSOVER": {
            "name": "Moving Average Crossover",
            "desc": "Golden Cross (Fast SMA > Slow SMA) for Buy; Death Cross for Sell.",
            "params": {"fast_period": 9, "slow_period": 21, "timeframe": "5m"}
        },
        "RSI_REVERSION": {
            "name": "RSI Mean Reversion",
            "desc": "Buys when RSI < Oversold threshold (30); Sells when RSI > Overbought threshold (70).",
            "params": {"period": 14, "oversold": 30, "overbought": 70, "timeframe": "15m"}
        },
        "BREAKOUT": {
            "name": "High/Low Range Breakout",
            "desc": "Enters Long when price breaks above N-candle High; Enters Short on N-candle Low break.",
            "params": {"lookback": 20, "timeframe": "15m"}
        },
        "GRID_TRADING": {
            "name": "Automated Grid Trading",
            "desc": "Executes systematic buy/sell orders at preset grid spacing intervals.",
            "params": {"grid_levels": 5, "spacing_pct": 0.5, "timeframe": "5m"}
        },
        "VWAP_TREND": {
            "name": "VWAP Trend Following",
            "desc": "Rides institutional trend momentum when price crosses Volume Weighted Average Price.",
            "params": {"timeframe": "1m"}
        }
    }

class AlgoEngine:
    def __init__(self):
        self.active_algos = {} # symbol -> {strategy_key, account_id, params, status}
        
    def get_presets(self):
        return StrategyPresets.STRATEGIES

    def toggle_algo(self, symbol, strategy_key, account_id, params=None):
        """Starts or stops an automated algo strategy on a symbol."""
        algo_id = f"{symbol}_{strategy_key}"
        if algo_id in self.active_algos and self.active_algos[algo_id]["status"] == "RUNNING":
            self.active_algos[algo_id]["status"] = "STOPPED"
            return {"status": "SUCCESS", "message": f"Strategy {strategy_key} for {symbol} STOPPED."}
        else:
            preset = StrategyPresets.STRATEGIES.get(strategy_key, {})
            strategy_params = dict(preset.get("params", {}))
            if params:
                strategy_params.update(params)
                
            self.active_algos[algo_id] = {
                "algo_id": algo_id,
                "symbol": symbol,
                "strategy_key": strategy_key,
                "strategy_name": preset.get("name", strategy_key),
                "account_id": account_id,
                "params": strategy_params,
                "status": "RUNNING",
                "signals_generated": 0,
                "last_signal": None,
                "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return {"status": "SUCCESS", "message": f"Strategy {preset.get('name')} STARTED on {symbol}."}

    def process_live_tick(self):
        """Evaluates active algos against latest market candles and generates live auto trades."""
        results = []
        for algo_id, algo in list(self.active_algos.items()):
            if algo["status"] != "RUNNING":
                continue
                
            symbol = algo["symbol"]
            strategy_key = algo["strategy_key"]
            tf = algo["params"].get("timeframe", "5m")
            candles = market_data_streamer.get_candles(symbol, tf)
            
            if len(candles) < 30:
                continue
                
            closes = [c["close"] for c in candles]
            curr_price = closes[-1]
            signal = None
            
            if strategy_key == "MA_CROSSOVER":
                fast_p = algo["params"].get("fast_period", 9)
                slow_p = algo["params"].get("slow_period", 21)
                fast_sma = TechnicalIndicators.sma(closes, fast_p)
                slow_sma = TechnicalIndicators.sma(closes, slow_p)
                
                # Check cross on last 2 bars
                if fast_sma[-2] <= slow_sma[-2] and fast_sma[-1] > slow_sma[-1]:
                    signal = "BUY"
                elif fast_sma[-2] >= slow_sma[-2] and fast_sma[-1] < slow_sma[-1]:
                    signal = "SELL"
                    
            elif strategy_key == "RSI_REVERSION":
                oversold = algo["params"].get("oversold", 30)
                overbought = algo["params"].get("overbought", 70)
                rsi = TechnicalIndicators.rsi(closes, algo["params"].get("period", 14))
                
                if rsi[-2] <= oversold and rsi[-1] > oversold:
                    signal = "BUY"
                elif rsi[-2] >= overbought and rsi[-1] < overbought:
                    signal = "SELL"

            elif strategy_key == "BREAKOUT":
                lookback = algo["params"].get("lookback", 20)
                recent_high = max(c["high"] for c in candles[-(lookback+1):-1])
                recent_low = min(c["low"] for c in candles[-(lookback+1):-1])
                
                if curr_price > recent_high:
                    signal = "BUY"
                elif curr_price < recent_low:
                    signal = "SELL"
                    
            elif strategy_key == "VWAP_TREND":
                df = pd.DataFrame(candles)
                vwap = TechnicalIndicators.vwap(df)
                if closes[-2] <= vwap[-2] and closes[-1] > vwap[-1]:
                    signal = "BUY"
                elif closes[-2] >= vwap[-2] and closes[-1] < vwap[-1]:
                    signal = "SELL"

            if signal and algo["last_signal"] != signal:
                algo["last_signal"] = signal
                algo["signals_generated"] += 1
                
                # Auto execute on specified Master account
                trade_res = account_manager.execute_order(
                    account_id=algo["account_id"],
                    symbol=symbol,
                    side=signal,
                    quantity=5, # Standard lot
                    strategy=algo["strategy_name"],
                    trigger_copier=True
                )
                results.append({"algo_id": algo_id, "signal": signal, "trade_result": trade_res})
                
        return results

    def run_backtest(self, symbol, strategy_key, timeframe="15m", initial_capital=1000000.0, params=None):
        """Runs historical backtest on symbol OHLCV data."""
        candles = market_data_streamer.get_candles(symbol, timeframe)
        if len(candles) < 40:
            return {"error": "Insufficient historical data for backtesting."}
            
        closes = [c["close"] for c in candles]
        df = pd.DataFrame(candles)
        
        capital = initial_capital
        equity_curve = [{"time": candles[0]["time_str"], "equity": capital}]
        trades = []
        position = None # {"side", "entry_price", "qty", "entry_time"}
        
        preset = StrategyPresets.STRATEGIES.get(strategy_key, {})
        strat_params = dict(preset.get("params", {}))
        if params:
            strat_params.update(params)
            
        for i in range(30, len(candles)):
            curr_candle = candles[i]
            c_price = curr_candle["close"]
            sub_closes = closes[:i+1]
            signal = None
            
            # Evaluate strategy signals
            if strategy_key == "MA_CROSSOVER":
                fast_sma = TechnicalIndicators.sma(sub_closes, strat_params.get("fast_period", 9))
                slow_sma = TechnicalIndicators.sma(sub_closes, strat_params.get("slow_period", 21))
                if fast_sma[-2] <= slow_sma[-2] and fast_sma[-1] > slow_sma[-1]:
                    signal = "BUY"
                elif fast_sma[-2] >= slow_sma[-2] and fast_sma[-1] < slow_sma[-1]:
                    signal = "SELL"
                    
            elif strategy_key == "RSI_REVERSION":
                rsi = TechnicalIndicators.rsi(sub_closes, 14)
                if rsi[-2] <= 30 and rsi[-1] > 30:
                    signal = "BUY"
                elif rsi[-2] >= 70 and rsi[-1] < 70:
                    signal = "SELL"

            elif strategy_key in ["BREAKOUT", "VWAP_TREND", "GRID_TRADING"]:
                # Default breakout simulation
                sub_df = df.iloc[:i+1]
                lookback = 20
                recent_high = sub_df["high"].iloc[-(lookback+1):-1].max()
                recent_low = sub_df["low"].iloc[-(lookback+1):-1].min()
                if c_price > recent_high:
                    signal = "BUY"
                elif c_price < recent_low:
                    signal = "SELL"

            # Execute trade logic in backtest
            qty = max(1, int((capital * 0.1) / c_price))
            
            if position:
                # Check exit / reverse
                if (position["side"] == "BUY" and signal == "SELL") or (position["side"] == "SELL" and signal == "BUY"):
                    pnl = (c_price - position["entry_price"]) * position["qty"] if position["side"] == "BUY" else (position["entry_price"] - c_price) * position["qty"]
                    capital += pnl
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": curr_candle["time_str"],
                        "side": position["side"],
                        "entry_price": position["entry_price"],
                        "exit_price": c_price,
                        "pnl": round(pnl, 2),
                        "return_pct": round((pnl / (position["entry_price"] * position["qty"])) * 100, 2)
                    })
                    position = None

            if signal and not position:
                position = {
                    "side": signal,
                    "entry_price": c_price,
                    "qty": qty,
                    "entry_time": curr_candle["time_str"]
                }
                
            equity_curve.append({"time": curr_candle["time_str"], "equity": round(capital, 2)})
            
        # Calculate statistics
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        total_pnl = capital - initial_capital
        win_rate = round((len(wins) / len(trades) * 100), 2) if trades else 0.0
        
        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        
        peak = initial_capital
        max_drawdown = 0.0
        for point in equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = ((peak - point["equity"]) / peak) * 100
            if dd > max_drawdown:
                max_drawdown = dd

        return {
            "summary": {
                "symbol": symbol,
                "strategy": preset.get("name", strategy_key),
                "timeframe": timeframe,
                "initial_capital": initial_capital,
                "final_equity": round(capital, 2),
                "net_profit": round(total_pnl, 2),
                "return_pct": round((total_pnl / initial_capital) * 100, 2),
                "total_trades": len(trades),
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "max_drawdown_pct": round(max_drawdown, 2),
                "sharpe_ratio": round((total_pnl / (initial_capital * 0.05 + 1e-5)), 2)
            },
            "equity_curve": equity_curve,
            "trades": trades[:30] # Top 30 trade entries
        }

# Global algo engine instance
algo_engine = AlgoEngine()
