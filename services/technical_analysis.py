"""
Technical Analysis Engine — pure numpy/pandas implementation
of RSI, MACD, Bollinger Bands, SMA/EMA for zero-dependency conflicts.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def _rsi(close: pd.Series, period: int = 14) -> float:
    """Compute RSI (Relative Strength Index)."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if not np.isnan(val) else 50.0


def _ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def _macd(close: pd.Series) -> dict:
    """Compute MACD."""
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)

    curr_macd = float(macd_line.iloc[-1])
    curr_signal = float(signal_line.iloc[-1])
    prev_macd = float(macd_line.iloc[-2]) if len(macd_line) > 1 else curr_macd
    prev_signal = float(signal_line.iloc[-2]) if len(signal_line) > 1 else curr_signal

    if prev_macd < prev_signal and curr_macd > curr_signal:
        return {"signal": "Bullish crossover", "value": round(curr_macd, 4)}
    elif prev_macd > prev_signal and curr_macd < curr_signal:
        return {"signal": "Bearish crossover", "value": round(curr_macd, 4)}
    elif curr_macd > curr_signal:
        return {"signal": "Bullish (above signal)", "value": round(curr_macd, 4)}
    else:
        return {"signal": "Bearish (below signal)", "value": round(curr_macd, 4)}


def _bollinger(close: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """Compute Bollinger Bands."""
    sma = _sma(close, period)
    std = close.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)

    curr_price = float(close.iloc[-1])
    curr_upper = float(upper.iloc[-1])
    curr_lower = float(lower.iloc[-1])

    if curr_price <= curr_lower * 1.02:
        status = "Price near lower band (potential reversal)"
    elif curr_price >= curr_upper * 0.98:
        status = "Price near upper band (potential pullback)"
    else:
        status = "Price within bands (normal range)"

    return {"status": status, "upper": round(curr_upper, 2), "lower": round(curr_lower, 2)}


def compute_indicators(hist: pd.DataFrame) -> Dict[str, Any]:
    """Compute all technical indicators from OHLCV data."""
    if hist is None or hist.empty or len(hist) < 20:
        return {"error": "Insufficient data", "score": 50, "verdict": "Analysis unavailable"}

    try:
        close = hist["Close"]
        high = hist["High"]
        low = hist["Low"]
        volume = hist["Volume"]
        current_price = float(close.iloc[-1])

        # RSI
        rsi = _rsi(close)

        # MACD
        macd_result = _macd(close)
        macd_signal = macd_result["signal"]

        # Bollinger Bands
        bb = _bollinger(close)
        bb_status = bb["status"]

        # Moving Averages
        sma_20 = float(_sma(close, 20).iloc[-1]) if len(close) >= 20 else None
        sma_50 = float(_sma(close, 50).iloc[-1]) if len(close) >= 50 else None
        sma_200 = float(_sma(close, 200).iloc[-1]) if len(close) >= 200 else None

        # Golden/Death Cross
        cross_signal = None
        if sma_50 is not None and sma_200 is not None and len(close) > 201:
            sma50_series = _sma(close, 50)
            sma200_series = _sma(close, 200)
            prev_50 = float(sma50_series.iloc[-2])
            prev_200 = float(sma200_series.iloc[-2])
            if prev_50 < prev_200 and sma_50 > sma_200:
                cross_signal = "Golden Cross (bullish)"
            elif prev_50 > prev_200 and sma_50 < sma_200:
                cross_signal = "Death Cross (bearish)"

        # Volume analysis
        avg_vol = float(volume.tail(20).mean())
        latest_vol = float(volume.iloc[-1])
        volume_ratio = round(latest_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # Trend
        if sma_20 and sma_50:
            if current_price > sma_20 > sma_50:
                trend = "Strong Uptrend"
            elif current_price > sma_20:
                trend = "Moderate Uptrend"
            elif current_price < sma_20 < sma_50:
                trend = "Strong Downtrend"
            elif current_price < sma_20:
                trend = "Moderate Downtrend"
            else:
                trend = "Sideways"
        else:
            trend = "Insufficient data"

        # Support / Resistance
        recent_high = float(high.tail(20).max())
        recent_low = float(low.tail(20).min())

        # Scoring (0-100)
        score = 50
        if rsi < 30: score += 15
        elif rsi > 70: score -= 15
        elif rsi < 45: score += 5
        elif rsi > 55: score -= 5

        if "Bullish" in macd_signal: score += 15
        elif "Bearish" in macd_signal: score -= 15

        if "lower band" in bb_status: score += 10
        elif "upper band" in bb_status: score -= 10

        if "Strong Uptrend" in trend: score += 10
        elif "Strong Downtrend" in trend: score -= 10

        if volume_ratio > 1.5: score += 5
        if cross_signal and "Golden" in cross_signal: score += 10
        elif cross_signal and "Death" in cross_signal: score -= 10

        score = max(0, min(100, score))

        # Verdict
        if score >= 70: verdict = "Strong technical setup for upside move"
        elif score >= 55: verdict = "Moderate bullish technical indicators"
        elif score >= 45: verdict = "Neutral — wait for confirmation"
        elif score >= 30: verdict = "Weak setup — bearish pressure building"
        else: verdict = "Strong bearish signals — caution advised"

        return {
            "rsi": rsi, "macd": macd_signal, "bollinger": bb_status,
            "trend": trend, "cross_signal": cross_signal,
            "volume_ratio": volume_ratio,
            "support": round(recent_low, 2), "resistance": round(recent_high, 2),
            "sma_20": round(sma_20, 2) if sma_20 else None,
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "sma_200": round(sma_200, 2) if sma_200 else None,
            "score": score, "verdict": verdict,
        }
    except Exception as e:
        logger.error(f"Technical analysis error: {e}")
        return {"error": str(e), "score": 50, "verdict": "Analysis unavailable"}
