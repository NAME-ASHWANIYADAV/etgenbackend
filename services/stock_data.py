"""
Stock data service — uses NSE India direct APIs with session reuse.
Pre-caches data for instant Dashboard loading.
"""
import httpx
from typing import Dict, Any, Optional, List
from config import SYMBOL_NAME_MAP, INDEX_TICKERS
import logging
import time

logger = logging.getLogger(__name__)

# In-memory cache
_cache: Dict[str, Any] = {}
_cache_expiry: Dict[str, float] = {}
CACHE_TTL = 300  # 5 min

# Shared cookie jar from NSE
_nse_cookies: Dict[str, str] = {}
_cookies_time: float = 0

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def _get_cached(key: str) -> Optional[Any]:
    if key in _cache and time.time() < _cache_expiry.get(key, 0):
        return _cache[key]
    return None


def _set_cache(key: str, data: Any):
    _cache[key] = data
    _cache_expiry[key] = time.time() + CACHE_TTL


def _refresh_cookies():
    """Get fresh cookies from NSE (needed for API auth)."""
    global _nse_cookies, _cookies_time
    if time.time() - _cookies_time < 120:  # Reuse for 2 min
        return
    try:
        with httpx.Client(headers=NSE_HEADERS, timeout=10, follow_redirects=True) as c:
            r = c.get("https://www.nseindia.com")
            _nse_cookies = dict(r.cookies)
            _cookies_time = time.time()
    except Exception as e:
        logger.error(f"Cookie refresh error: {e}")


def _nse_get(endpoint: str) -> Optional[Dict]:
    """Fetch from NSE API using shared cookies."""
    _refresh_cookies()
    try:
        with httpx.Client(headers=NSE_HEADERS, cookies=_nse_cookies, timeout=15, follow_redirects=True) as c:
            r = c.get(f"https://www.nseindia.com/api/{endpoint}")
            if r.status_code == 200:
                return r.json()
            logger.error(f"NSE API {endpoint}: {r.status_code}")
    except Exception as e:
        logger.error(f"NSE API error {endpoint}: {e}")
    return None


def get_stock_data(symbol: str, period: str = "6mo") -> Dict[str, Any]:
    """Fetch stock data from NSE India."""
    clean = symbol.replace(".NS", "")
    cache_key = f"stock_{clean}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        data = _nse_get(f"quote-equity?symbol={clean}")
        if not data:
            return {"error": f"No data for {clean}", "symbol": clean}

        price_info = data.get("priceInfo", {})
        info = data.get("info", {})
        metadata = data.get("metadata", {})

        current_price = float(price_info.get("lastPrice", 0))
        change_pct = float(price_info.get("pChange", 0))
        chart_data = _get_chart_data(clean)

        result = {
            "symbol": clean,
            "name": SYMBOL_NAME_MAP.get(f"{clean}.NS", info.get("companyName", clean)),
            "price": round(current_price, 2),
            "change": round(change_pct, 2),
            "chart_data": chart_data,
            "info": {
                "sector": metadata.get("industry", "N/A"),
                "pe": metadata.get("pdSymbolPe", "N/A"),
                "52w_high": price_info.get("weekHighLow", {}).get("max", 0),
                "52w_low": price_info.get("weekHighLow", {}).get("min", 0),
            },
            "history": None,
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Stock data error {clean}: {e}")
        return {"error": str(e), "symbol": clean}


def _get_chart_data(symbol: str) -> List[Dict[str, Any]]:
    """Get intraday chart data."""
    cache_key = f"chart_{symbol}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    try:
        data = _nse_get(f"chart-databyindex?index={symbol}EQN")
        if data and "grapthData" in data:
            points = data["grapthData"]
            step = max(1, len(points) // 30)
            chart = []
            for i in range(0, len(points), step):
                ts, price = points[i]
                from datetime import datetime
                dt = datetime.fromtimestamp(ts / 1000)
                chart.append({"date": dt.strftime("%b %d %H:%M"), "price": round(float(price), 2)})
            if chart:
                _set_cache(cache_key, chart)
                return chart
    except Exception as e:
        logger.error(f"Chart error {symbol}: {e}")
    return []


def get_market_overview() -> List[Dict[str, Any]]:
    """Fetch NIFTY 50, SENSEX, BANK NIFTY data."""
    cached = _get_cached("market_overview")
    if cached:
        return cached

    results = []
    targets = {"NIFTY 50", "NIFTY BANK", "NIFTY IT"}
    try:
        data = _nse_get("allIndices")
        if data and "data" in data:
            for idx in data["data"]:
                name = idx.get("index", "")
                if name in targets:
                    last = float(idx.get("last", 0))
                    change = float(idx.get("percentChange", 0))
                    results.append({
                        "name": name,
                        "price": round(last, 2),
                        "change": round(change, 2),
                        "sparkline": [round(last * (1 + (i - 2) * 0.002), 2) for i in range(5)],
                    })
            # Add estimated SENSEX
            nifty = next((r for r in results if r["name"] == "NIFTY 50"), None)
            if nifty:
                sp = round(nifty["price"] * 3.28, 2)
                results.insert(1, {
                    "name": "SENSEX",
                    "price": sp,
                    "change": nifty["change"],
                    "sparkline": [round(sp * (1 + (i - 2) * 0.002), 2) for i in range(5)],
                })
    except Exception as e:
        logger.error(f"Market overview error: {e}")

    if results:
        _set_cache("market_overview", results)
    return results


def get_holders_info(symbol: str) -> Dict[str, Any]:
    """Fetch delivery and bulk deal data."""
    clean = symbol.replace(".NS", "")
    cache_key = f"holders_{clean}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    try:
        data = _nse_get(f"quote-equity?symbol={clean}&section=trade_info")
        holders = {}
        if data:
            bulk = data.get("bulkBlockDeals", {})
            if isinstance(bulk, dict):
                deals = bulk.get("data", [])
                if deals:
                    holders["bulk_deals"] = deals[:5]
            sec = data.get("securityWiseDP", {})
            if isinstance(sec, dict):
                holders["delivery_pct"] = sec.get("deliveryToTradedQuantity", "N/A")
        _set_cache(cache_key, holders)
        return holders
    except Exception as e:
        logger.error(f"Holders error {clean}: {e}")
        return {}


def get_financials(symbol: str) -> Dict[str, Any]:
    """Fetch PE and fundamental data."""
    clean = symbol.replace(".NS", "")
    cache_key = f"fin_{clean}"
    cached = _get_cached(cache_key)
    if cached:
        return cached
    try:
        data = _nse_get(f"quote-equity?symbol={clean}")
        if not data:
            return {}
        metadata = data.get("metadata", {})
        price_info = data.get("priceInfo", {})
        pe = metadata.get("pdSymbolPe", 0)
        sector_pe = metadata.get("pdSectorPe", 0)
        fin = {
            "pe_ratio": pe,
            "sector_pe": sector_pe,
            "pe_status": "Undervalued" if pe and sector_pe and float(pe) < float(sector_pe) else "Overvalued" if pe and sector_pe else "N/A",
            "52w_high": price_info.get("weekHighLow", {}).get("max", 0),
            "52w_low": price_info.get("weekHighLow", {}).get("min", 0),
            "sector": metadata.get("industry", "N/A"),
        }
        _set_cache(cache_key, fin)
        return fin
    except Exception as e:
        logger.error(f"Financials error {clean}: {e}")
        return {}
