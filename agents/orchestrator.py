"""
Orchestrator Agent — uses Gemini LLM for natural language market Q&A.
Coordinates with all agents and provides portfolio-aware responses.
"""
import google.generativeai as genai
from config import GEMINI_API_KEY
from typing import Dict, Any, Optional
import logging
import re
import concurrent.futures

logger = logging.getLogger(__name__)

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Expanded stock mappings — 50+ Indian stocks
NAME_TO_SYMBOL = {
    # Banks
    "hdfc bank": "HDFCBANK", "hdfc": "HDFCBANK",
    "icici bank": "ICICIBANK", "icici": "ICICIBANK",
    "sbi": "SBIN", "state bank": "SBIN", "state bank of india": "SBIN",
    "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK", "kotak mahindra": "KOTAKBANK",
    "axis bank": "AXISBANK", "axis": "AXISBANK",
    "indusind bank": "INDUSINDBK", "indusind": "INDUSINDBK",
    "punjab national bank": "PNB", "pnb": "PNB",
    "bank of baroda": "BANKBARODA", "bob": "BANKBARODA",
    "canara bank": "CANBK",
    # IT
    "tcs": "TCS", "tata consultancy": "TCS",
    "infosys": "INFY", "infy": "INFY",
    "wipro": "WIPRO",
    "hcl tech": "HCLTECH", "hcltech": "HCLTECH", "hcl": "HCLTECH",
    "tech mahindra": "TECHM", "techm": "TECHM",
    "ltimindtree": "LTIM", "ltim": "LTIM",
    "persistent": "PERSISTENT",
    "coforge": "COFORGE",
    # Conglomerates/Oil
    "reliance": "RELIANCE", "ril": "RELIANCE", "reliance industries": "RELIANCE",
    "adani": "ADANIENT", "adani enterprises": "ADANIENT",
    "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN",
    "adani power": "ADANIPOWER",
    "tata": "TATASTEEL",
    "l&t": "LT", "larsen": "LT", "larsen & toubro": "LT",
    # Auto
    "tata motors": "TATAMOTORS", "tata motor": "TATAMOTORS", "tatamotors": "TATAMOTORS",
    "maruti": "MARUTI", "maruti suzuki": "MARUTI",
    "mahindra": "M&M", "m&m": "M&M", "mahindra and mahindra": "M&M",
    "bajaj auto": "BAJAJ-AUTO",
    "hero motocorp": "HEROMOTOCO", "hero": "HEROMOTOCO",
    "eicher": "EICHERMOT", "royal enfield": "EICHERMOT",
    # FMCG
    "itc": "ITC",
    "hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR",
    "nestle": "NESTLEIND", "nestle india": "NESTLEIND",
    "britannia": "BRITANNIA",
    "dabur": "DABUR",
    "marico": "MARICO",
    "godrej": "GODREJCP",
    "colgate": "COLPAL",
    # Pharma
    "sun pharma": "SUNPHARMA", "sun pharmaceutical": "SUNPHARMA",
    "dr reddy": "DRREDDY", "dr reddys": "DRREDDY",
    "cipla": "CIPLA",
    "divi's": "DIVISLAB", "divis lab": "DIVISLAB",
    "biocon": "BIOCON",
    # Telecom
    "airtel": "BHARTIARTL", "bharti airtel": "BHARTIARTL", "bharti": "BHARTIARTL",
    "jio": "RELIANCE", "jio financial": "JIOFIN",
    "vodafone idea": "IDEA", "vi": "IDEA",
    # Finance
    "bajaj finance": "BAJFINANCE", "bajfinance": "BAJFINANCE",
    "bajaj finserv": "BAJFINANCE",
    "sbi life": "SBILIFE",
    "hdfc life": "HDFCLIFE",
    "icici prudential": "ICICIPRULI",
    # Power/Infra
    "power grid": "POWERGRID", "powergrid": "POWERGRID",
    "ntpc": "NTPC",
    "tata power": "TATAPOWER",
    "adani energy": "ADANIENT",
    # Metal
    "tata steel": "TATASTEEL",
    "hindalco": "HINDALCO",
    "jsw steel": "JSWSTEEL", "jsw": "JSWSTEEL",
    "vedanta": "VEDL",
    # Others
    "asian paints": "ASIANPAINT", "asian paint": "ASIANPAINT",
    "titan": "TITAN",
    "pidilite": "PIDILITIND",
    "havells": "HAVELLS",
    "paytm": "PAYTM",
    "zomato": "ZOMATO",
    "nykaa": "NYKAA",
    "dmart": "DMART", "avenue supermarts": "DMART",
    "policybazaar": "POLICYBZR", "pb fintech": "POLICYBZR",
    "ola electric": "OLAELEC",
    "swiggy": "SWIGGY",
    "pw": "MOTHERSON", # Common abbreviation
    "coal india": "COALINDIA",
    "irctc": "IRCTC",
    "indian railway": "IRCTC",
    "ongc": "ONGC",
    "ioc": "IOC", "indian oil": "IOC",
    "bpcl": "BPCL",
    "gail": "GAIL",
    "ultratech": "ULTRACEMCO", "ultratech cement": "ULTRACEMCO",
    "shree cement": "SHREECEM",
}


def _extract_symbol(message: str) -> Optional[str]:
    """Extract stock symbol from user message using mappings."""
    msg_lower = message.lower().strip()

    # Direct symbol match (full message is a ticker)
    if msg_lower.upper() in [v for v in NAME_TO_SYMBOL.values()]:
        return msg_lower.upper()

    # Name mapping match (longest match first)
    sorted_names = sorted(NAME_TO_SYMBOL.keys(), key=len, reverse=True)
    for name in sorted_names:
        if name in msg_lower:
            return NAME_TO_SYMBOL[name]

    # Uppercase ticker pattern
    tickers = re.findall(r'\b[A-Z]{2,15}\b', message)
    if tickers:
        return tickers[0]

    return None


def _gemini_extract_symbol(message: str) -> Optional[str]:
    """Use Gemini to identify stock from natural language."""
    if not GEMINI_API_KEY:
        return None
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(
            f"""Extract NSE stock symbol from this query. Return ONLY the NSE ticker symbol (e.g., RELIANCE, TCS, HDFCBANK) or "NONE" if no specific Indian stock is mentioned.
Query: "{message}"
Symbol:""",
            generation_config=genai.GenerationConfig(temperature=0, max_output_tokens=20),
        )
        symbol = resp.text.strip().upper().replace('"', '').replace("'", "")
        if symbol and symbol != "NONE" and len(symbol) <= 20:
            return symbol
    except Exception as e:
        logger.error(f"Gemini symbol extraction error: {e}")
    return None


def chat(message: str) -> Dict[str, Any]:
    """Process a market query using Gemini + agent data."""

    # Step 1: Try hardcoded mapping first (fast)
    symbol = _extract_symbol(message)

    # Step 2: If not found, ask Gemini to identify (slower but smarter)
    if not symbol:
        symbol = _gemini_extract_symbol(message)

    agent_data = None
    agents_used = []
    sources = []

    if symbol:
        try:
            from agents.signal_fusion import analyze_stock_full
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(analyze_stock_full, symbol)
                agent_data = future.result(timeout=25)
            agents_used = ["📊 Technical", "📑 Filing", "🔍 Insider", "📰 Sentiment"]
            sources = [
                f"ET Markets, {__import__('datetime').date.today().strftime('%B %d, %Y')}",
                f"BSE/NSE Filing Data — {symbol}",
                f"NSE India — {symbol}",
            ]
        except concurrent.futures.TimeoutError:
            logger.error(f"Agent analysis timed out for {symbol}")
        except Exception as e:
            logger.error(f"Agent data fetch error: {e}")

    # Build context for Gemini
    context = ""
    if agent_data:
        tech = agent_data.get("technical", {})
        filing = agent_data.get("filing", {})
        insider = agent_data.get("insider", {})
        sentiment = agent_data.get("sentiment", {})
        fusion = agent_data.get("fusion", {})

        context = f"""
REAL-TIME AGENT DATA FOR {symbol} ({agent_data.get('name', symbol)}):
Current Price: ₹{agent_data.get('price', 'N/A')} ({agent_data.get('change', 0):+.1f}%)

TECHNICAL ANALYSIS AGENT (Score: {tech.get('score', 'N/A')}/100):
- RSI: {tech.get('rsi', 'N/A')}
- MACD: {tech.get('macd', 'N/A')}
- Bollinger Bands: {tech.get('bollinger', 'N/A')}
- Verdict: {tech.get('verdict', 'N/A')}

FILING & FUNDAMENTALS AGENT (Score: {filing.get('score', 'N/A')}/100):
- Revenue: {filing.get('revenue', 'N/A')}
- Profit: {filing.get('profit', 'N/A')}
- Highlight: {filing.get('highlight', 'N/A')}
- Verdict: {filing.get('verdict', 'N/A')}

INSIDER ACTIVITY AGENT (Score: {insider.get('score', 'N/A')}/100):
- Recent Activity: {insider.get('recent', 'N/A')}
- Holding: {insider.get('holding', 'N/A')}
- Pledge: {insider.get('pledge', 'N/A')}
- Verdict: {insider.get('verdict', 'N/A')}

NEWS SENTIMENT AGENT (Score: {sentiment.get('score', 'N/A')}/100):
- Articles Analyzed: {sentiment.get('articles_count', 0)}
- Sentiment Score: {sentiment.get('sentiment_score', 'N/A')}
- Verdict: {sentiment.get('verdict', 'N/A')}

SIGNAL FUSION ENGINE (Composite Score: {fusion.get('score', 'N/A')}/100):
- {fusion.get('convergence', '')}
- {fusion.get('backtest', '')}
- Final Verdict: {fusion.get('verdict', '')}
"""

    # Use Gemini for response
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")

            system_prompt = f"""You are the Opportunity Radar Market Intelligence AI — a multi-agent financial analysis system for Indian investors. You provide data-driven, actionable investment insights.

RULES:
1. Always cite specific data from the agent analysis provided
2. Structure your response with agent sections (📊 Technical, 📑 Fundamentals, 🔍 Insider, 📰 Sentiment, ⚡ Signal Fusion)
3. End with a clear verdict (BUY/SELL/HOLD with conviction score)
4. Add a disclaimer: "This is AI-generated analysis for informational purposes. Not investment advice."
5. Keep responses concise but data-rich
6. If no specific stock data is available, provide general market guidance
7. Use ₹ for Indian currency
8. Reference ET Markets and NSE/BSE as sources

{context}
"""

            response = model.generate_content(
                f"{system_prompt}\n\nUser question: {message}",
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1500,
                )
            )

            return {
                "response": response.text,
                "agents": agents_used,
                "sources": sources,
            }

        except Exception as e:
            logger.error(f"Gemini API error: {e}")

    # Fallback without LLM
    if agent_data:
        fusion = agent_data.get("fusion", {})
        tech = agent_data.get("technical", {})
        filing = agent_data.get("filing", {})
        insider = agent_data.get("insider", {})
        sentiment = agent_data.get("sentiment", {})

        response = f"""Based on my multi-agent analysis of {agent_data.get('name', symbol)} (NSE: {symbol}):

**Overall Signal: {fusion.get('signal', 'HOLD')} with {'High' if fusion.get('score', 50) > 70 else 'Moderate' if fusion.get('score', 50) > 50 else 'Low'} Conviction ({fusion.get('score', 50)}/100)**

📊 **Technical Setup:** RSI at {tech.get('rsi', 'N/A')}, {tech.get('macd', 'N/A')}. {tech.get('bollinger', '')}. {tech.get('verdict', '')}

📑 **Fundamentals:** {filing.get('revenue', 'N/A')}, {filing.get('profit', 'N/A')}. {filing.get('highlight', '')}. {filing.get('verdict', '')}

🔍 **Insider Activity:** {insider.get('recent', 'N/A')}. {insider.get('holding', 'N/A')}. {insider.get('verdict', '')}

📰 **Market Sentiment:** {sentiment.get('articles_count', 0)} articles analyzed. {sentiment.get('verdict', '')}

⚡ **Signal Fusion:** {fusion.get('convergence', '')}. {fusion.get('backtest', '')}

*This is AI-generated analysis for informational purposes. Not investment advice.*"""

        return {
            "response": response,
            "agents": agents_used,
            "sources": sources,
        }

    return {
        "response": """Welcome to **Opportunity Radar** — your AI-powered market intelligence system! 🔥

I can provide deep, multi-agent analysis on any NSE-listed stock. Here's what I can do:

📊 **Technical Analysis** — RSI, MACD, Bollinger Bands, Golden/Death Cross, breakout detection
📑 **Filing & Fundamentals** — Quarterly results, revenue/profit growth, PE analysis
🔍 **Insider Activity** — Institutional holdings, promoter movements, block deals
📰 **News Sentiment** — ET Markets & financial news sentiment scoring
⚡ **Signal Fusion** — Cross-agent correlation for high-conviction signals

**Try asking:**
- "Should I buy HDFC Bank?"
- "Analyze Reliance"
- "What about TCS?"
- "Is Infosys a good investment?"

*Powered by real-time NSE/BSE data and AI-driven analysis.*""",
        "agents": ["📊 Technical", "📑 Filing", "🔍 Insider", "📰 Sentiment", "⚡ Fusion"],
        "sources": ["NSE India", "BSE India", "ET Markets"],
    }
