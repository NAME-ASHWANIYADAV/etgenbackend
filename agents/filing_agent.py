"""
Filing & Fundamentals Agent — analyzes NSE financial data.
PE ratio, 52-week range, sector comparison.
"""
from services.stock_data import get_stock_data, get_financials
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def analyze(symbol: str) -> Dict[str, Any]:
    """Analyze fundamentals for a stock using NSE data."""
    try:
        stock = get_stock_data(symbol)
        fin = get_financials(symbol)

        if "error" in stock and not stock.get("price"):
            return _fallback(symbol)

        price = stock.get("price", 0)
        info = stock.get("info", {})
        pe = fin.get("pe_ratio", "N/A")
        sector_pe = fin.get("sector_pe", "N/A")
        pe_status = fin.get("pe_status", "N/A")
        high_52 = fin.get("52w_high", info.get("52w_high", 0))
        low_52 = fin.get("52w_low", info.get("52w_low", 0))
        sector = fin.get("sector", info.get("sector", "N/A"))

        # Score based on PE and position
        score = 50
        if pe and pe != "N/A" and sector_pe and sector_pe != "N/A":
            try:
                pe_val = float(pe)
                sector_val = float(sector_pe)
                if pe_val < sector_val * 0.8:
                    score += 20  # Undervalued
                elif pe_val < sector_val:
                    score += 10
                elif pe_val > sector_val * 1.3:
                    score -= 15  # Overvalued
                elif pe_val > sector_val:
                    score -= 5
            except (ValueError, TypeError):
                pass

        # 52-week position analysis
        if high_52 and low_52 and price:
            try:
                range_52 = float(high_52) - float(low_52)
                if range_52 > 0:
                    pos = (price - float(low_52)) / range_52
                    if pos < 0.3:
                        score += 10  # Near 52-week low
                    elif pos > 0.9:
                        score -= 5   # Near 52-week high
            except (ValueError, TypeError):
                pass

        score = max(0, min(100, score))

        if score >= 60:
            signal = "BUY"
        elif score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Generate readable values
        pe_str = f"PE: {pe}" if pe != "N/A" else "PE: N/A"
        sector_str = f"Sector PE: {sector_pe}" if sector_pe != "N/A" else ""
        range_str = f"₹{low_52} — ₹{high_52}" if high_52 else "N/A"

        # Verdict
        if score >= 70:
            verdict = f"Fundamentally strong — {pe_status} vs sector"
        elif score >= 55:
            verdict = f"Decent fundamentals — {pe_status}"
        elif score >= 45:
            verdict = "Mixed fundamentals — needs deeper analysis"
        elif score >= 30:
            verdict = "Weak fundamentals — overvalued indicators"
        else:
            verdict = "Poor fundamentals — significant overvaluation risk"

        # Chip label
        if pe_status == "Undervalued":
            chip = f"Filing: {pe_status} (PE {pe})"
        elif pe_status == "Overvalued":
            chip = f"Filing: {pe_status} (PE {pe})"
        else:
            chip = f"Filing: PE {pe}"

        return {
            "score": score,
            "signal": signal,
            "revenue": f"Sector: {sector}",
            "profit": pe_str,
            "highlight": f"52W Range: {range_str} | {sector_str}",
            "verdict": verdict,
            "chip_label": chip,
            "pe": pe,
            "sector_pe": sector_pe,
        }

    except Exception as e:
        logger.error(f"Filing analysis error for {symbol}: {e}")
        return _fallback(symbol)


def _fallback(symbol: str) -> Dict[str, Any]:
    return {
        "score": 50, "signal": "HOLD",
        "revenue": "N/A", "profit": "N/A",
        "highlight": "Data unavailable",
        "verdict": "Unable to analyze fundamentals",
        "chip_label": "Filing: Unavailable",
    }
