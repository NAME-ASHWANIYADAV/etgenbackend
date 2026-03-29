import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Top NSE stocks to scan for signals
WATCHLIST = [
    "HDFCBANK.NS", "RELIANCE.NS", "TATAMOTORS.NS", "INFY.NS",
    "TCS.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS",
    "BHARTIARTL.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "LT.NS",
    "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "WIPRO.NS",
    "HCLTECH.NS", "ADANIENT.NS", "TATASTEEL.NS", "POWERGRID.NS"
]

SYMBOL_NAME_MAP = {
    "HDFCBANK.NS": "HDFC Bank",
    "RELIANCE.NS": "Reliance Industries",
    "TATAMOTORS.NS": "Tata Motors",
    "INFY.NS": "Infosys",
    "TCS.NS": "TCS",
    "ITC.NS": "ITC Limited",
    "SBIN.NS": "State Bank of India",
    "BAJFINANCE.NS": "Bajaj Finance",
    "BHARTIARTL.NS": "Bharti Airtel",
    "ICICIBANK.NS": "ICICI Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "LT.NS": "Larsen & Toubro",
    "AXISBANK.NS": "Axis Bank",
    "MARUTI.NS": "Maruti Suzuki",
    "SUNPHARMA.NS": "Sun Pharma",
    "WIPRO.NS": "Wipro",
    "HCLTECH.NS": "HCL Technologies",
    "ADANIENT.NS": "Adani Enterprises",
    "TATASTEEL.NS": "Tata Steel",
    "POWERGRID.NS": "Power Grid",
}

INDEX_TICKERS = {
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
}
