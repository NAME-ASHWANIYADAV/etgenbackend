"""
Insider Activity Agent — analyzes bulk/block deals and delivery data from NSE.
"""
from services.stock_data import get_holders_info, get_stock_data
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def analyze(symbol: str) -> Dict[str, Any]:
    """Analyze insider/institutional activity."""
    try:
        holders = get_holders_info(symbol)
        stock = get_stock_data(symbol)

        score = 50
        bulk_deals = holders.get("bulk_deals", [])
        delivery_pct = holders.get("delivery_pct", "N/A")

        # Delivery percentage analysis
        recent_activity = "No major bulk/block deals"
        if bulk_deals:
            recent_activity = f"{len(bulk_deals)} bulk deal(s) detected"
            score += 15  # Bulk deals indicate institutional interest

        # Delivery analysis
        holding_str = "N/A"
        if delivery_pct and delivery_pct != "N/A":
            try:
                del_val = float(delivery_pct)
                holding_str = f"Delivery: {del_val}%"
                if del_val > 60:
                    score += 15  # High delivery = strong conviction
                elif del_val > 40:
                    score += 5
                elif del_val < 20:
                    score -= 10  # Low delivery = speculative
            except (ValueError, TypeError):
                holding_str = f"Delivery: {delivery_pct}"

        score = max(0, min(100, score))

        if score >= 60:
            signal = "BUY"
        elif score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Verdict
        if score >= 70:
            verdict = "Strong institutional interest — smart money active"
        elif score >= 55:
            verdict = "Moderate institutional activity"
        elif score >= 45:
            verdict = "Normal activity — no significant signals"
        elif score >= 30:
            verdict = "Low institutional interest"
        else:
            verdict = "Institutional selling pressure detected"

        # Chip
        if bulk_deals:
            chip = f"Insider: {len(bulk_deals)} Bulk Deal(s)"
        elif delivery_pct and delivery_pct != "N/A":
            chip = f"Insider: {delivery_pct}% Delivery"
        else:
            chip = "Insider: No major activity"

        return {
            "score": score,
            "signal": signal,
            "recent": recent_activity,
            "holding": holding_str,
            "pledge": "N/A",
            "verdict": verdict,
            "chip_label": chip,
        }

    except Exception as e:
        logger.error(f"Insider analysis error for {symbol}: {e}")
        return {
            "score": 50, "signal": "HOLD",
            "recent": "N/A", "holding": "N/A", "pledge": "N/A",
            "verdict": "Unable to analyze insider activity",
            "chip_label": "Insider: Unavailable",
        }
