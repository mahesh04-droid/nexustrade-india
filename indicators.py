"""
Antigravity AlgoTrader Pro - Technical Analysis Indicators Engine
"""

import numpy as np
import pandas as pd

class TechnicalIndicators:
    @staticmethod
    def sma(series, period=14):
        """Simple Moving Average"""
        s = pd.Series(series)
        return s.rolling(window=period).mean().to_numpy()

    @staticmethod
    def ema(series, period=14):
        """Exponential Moving Average"""
        s = pd.Series(series)
        return s.ewm(span=period, adjust=False).mean().to_numpy()

    @staticmethod
    def rsi(series, period=14):
        """Relative Strength Index"""
        s = pd.Series(series)
        delta = s.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi.to_numpy()

    @staticmethod
    def macd(series, fast=12, slow=26, signal=9):
        """Moving Average Convergence Divergence"""
        s = pd.Series(series)
        ema_fast = s.ewm(span=fast, adjust=False).mean()
        ema_slow = s.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        
        return {
            "macd": macd_line.to_numpy(),
            "signal": signal_line.to_numpy(),
            "histogram": hist.to_numpy()
        }

    @staticmethod
    def bollinger_bands(series, period=20, std_dev=2):
        """Bollinger Bands"""
        s = pd.Series(series)
        middle = s.rolling(window=period).mean()
        std = s.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {
            "middle": middle.to_numpy(),
            "upper": upper.to_numpy(),
            "lower": lower.to_numpy()
        }

    @staticmethod
    def vwap(df):
        """Volume Weighted Average Price"""
        # Expects dataframe or dict with high, low, close, volume
        typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
        vwap = (typical_price * df["volume"]).cumsum() / (df["volume"].cumsum() + 1e-9)
        return vwap.to_numpy()

    @classmethod
    def calculate_all(cls, candles):
        """Calculates indicators on OHLCV candle dictionary list."""
        if not candles or len(candles) < 20:
            return {}
            
        df = pd.DataFrame(candles)
        closes = df["close"].values
        
        sma_20 = np.nan_to_num(cls.sma(closes, 20), nan=0.0)
        sma_50 = np.nan_to_num(cls.sma(closes, 50), nan=0.0)
        ema_9 = np.nan_to_num(cls.ema(closes, 9), nan=0.0)
        rsi_14 = np.nan_to_num(cls.rsi(closes, 14), nan=50.0)
        macd_res = cls.macd(closes)
        bb_res = cls.bollinger_bands(closes)
        vwap_res = np.nan_to_num(cls.vwap(df), nan=closes[0])
        
        return {
            "sma_20": [round(float(v), 2) for v in sma_20],
            "sma_50": [round(float(v), 2) for v in sma_50],
            "ema_9": [round(float(v), 2) for v in ema_9],
            "rsi_14": [round(float(v), 2) for v in rsi_14],
            "macd": [round(float(v), 2) for v in np.nan_to_num(macd_res["macd"], nan=0.0)],
            "macd_signal": [round(float(v), 2) for v in np.nan_to_num(macd_res["signal"], nan=0.0)],
            "macd_hist": [round(float(v), 2) for v in np.nan_to_num(macd_res["histogram"], nan=0.0)],
            "bb_upper": [round(float(v), 2) for v in np.nan_to_num(bb_res["upper"], nan=closes[0])],
            "bb_middle": [round(float(v), 2) for v in np.nan_to_num(bb_res["middle"], nan=closes[0])],
            "bb_lower": [round(float(v), 2) for v in np.nan_to_num(bb_res["lower"], nan=closes[0])],
            "vwap": [round(float(v), 2) for v in vwap_res]
        }
