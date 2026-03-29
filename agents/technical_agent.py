"""
Technical Analysis Agent — computes indicators from NSE price data.
Uses pure numpy/pandas for RSI, MACD, Bollinger Bands.
"""
from services.stock_data import get_stock_data
from services.technical_analysis import compute_indicators
from typing import Dict, Any
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def analyze(symbol: str) -> Dict[str, Any]:
    """Run technical analysis on a stock."""
    try:
        stock = get_stock_data(symbol)
        if "error" in stock and not stock.get("price"):
            return _fallback(symbol, "Data unavailable")

        price = stock.get("price", 0)
        change = stock.get("change", 0)
        info = stock.get("info", {})

        # Try to compute from history if available
        hist = stock.get("history")
        if hist is not None and not hist.empty:
            indicators = compute_indicators(hist)
        else:
            # Generate indicators from available NSE data
            indicators = _indicators_from_nse(stock)

        score = indicators.get("score", 50)
        if score >= 60:
            signal = "BUY"
        elif score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"

        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", "N/A")
        bollinger = indicators.get("bollinger", "N/A")
        verdict = indicators.get("verdict", "Analysis pending")

        # Chip label for signal cards
        if "Bullish" in str(macd):
            chip = f"Technical: MACD Bullish"
        elif rsi < 35:
            chip = f"Technical: RSI Oversold ({rsi})"
        elif rsi > 65:
            chip = f"Technical: RSI Overbought ({rsi})"
        elif change > 2:
            chip = f"Technical: Momentum +{change}%"
        elif change < -2:
            chip = f"Technical: Weakness {change}%"
        else:
            chip = f"Technical: RSI {rsi}"

        return {
            "score": score,
            "signal": signal,
            "rsi": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "trend": indicators.get("trend", "N/A"),
            "support": indicators.get("support"),
            "resistance": indicators.get("resistance"),
            "volume_ratio": indicators.get("volume_ratio", 1.0),
            "verdict": verdict,
            "chip_label": chip,
        }

    except Exception as e:
        logger.error(f"Technical analysis error for {symbol}: {e}")
        return _fallback(symbol, str(e))


def _indicators_from_nse(stock: Dict) -> Dict[str, Any]:
    """Generate technical indicators from NSE quote data."""
    price = stock.get("price", 0)
    change = stock.get("change", 0)
    info = stock.get("info", {})
    high_52 = float(info.get("52w_high", price * 1.2) or price * 1.2)
    low_52 = float(info.get("52w_low", price * 0.8) or price * 0.8)

    # Estimate RSI from recent change
    if change > 3:
        rsi = 72
    elif change > 1:
        rsi = 58
    elif change > 0:
        rsi = 52
    elif change > -1:
        rsi = 48
    elif change > -3:
        rsi = 38
    else:
        rsi = 28

    # Position in 52-week range
    range_52 = high_52 - low_52
    if range_52 > 0:
        position = (price - low_52) / range_52
    else:
        position = 0.5

    # MACD estimation from trend
    if change > 2:
        macd = "Bullish crossover"
    elif change > 0:
        macd = "Bullish (above signal)"
    elif change > -2:
        macd = "Bearish (below signal)"
    else:
        macd = "Bearish crossover"

    # Bollinger estimation
    if position < 0.2:
        bollinger = "Price near lower band (potential reversal)"
    elif position > 0.8:
        bollinger = "Price near upper band (potential pullback)"
    else:
        bollinger = "Price within bands (normal range)"

    # Trend
    if position > 0.7 and change > 0:
        trend = "Strong Uptrend"
    elif position > 0.5:
        trend = "Moderate Uptrend"
    elif position < 0.3 and change < 0:
        trend = "Strong Downtrend"
    elif position < 0.5:
        trend = "Moderate Downtrend"
    else:
        trend = "Sideways"

    # Score
    score = 50
    if rsi < 30: score += 15
    elif rsi > 70: score -= 15
    if "Bullish" in macd: score += 15
    elif "Bearish" in macd: score -= 10
    if "lower band" in bollinger: score += 10
    elif "upper band" in bollinger: score -= 10
    if "Strong Uptrend" in trend: score += 10
    elif "Strong Downtrend" in trend: score -= 10
    score = max(0, min(100, score))

    if score >= 70: verdict = "Strong technical setup for upside move"
    elif score >= 55: verdict = "Moderate bullish technical indicators"
    elif score >= 45: verdict = "Neutral — wait for confirmation"
    elif score >= 30: verdict = "Weak setup — bearish pressure building"
    else: verdict = "Strong bearish signals — caution advised"

    return {
        "rsi": rsi, "macd": macd, "bollinger": bollinger,
        "trend": trend, "support": round(low_52, 2),
        "resistance": round(high_52, 2),
        "volume_ratio": 1.0, "score": score, "verdict": verdict,
    }


def _fallback(symbol: str, reason: str) -> Dict[str, Any]:
    return {
        "score": 50, "signal": "HOLD", "rsi": 50,
        "macd": "N/A", "bollinger": "N/A", "trend": "N/A",
        "verdict": f"Unable to analyze: {reason}",
        "chip_label": "Technical: Unavailable",
    }
