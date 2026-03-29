"""
News Sentiment Agent — scrapes financial news for sentiment analysis.
Uses RSS feeds and simple keyword sentiment scoring.
"""
from services.news_scraper import scrape_news
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "buy", "bullish", "growth", "profit", "surge", "rally", "upgrade", "outperform",
    "beat", "strong", "positive", "gain", "rise", "high", "expansion", "upside",
    "recommend", "target", "breakout", "momentum", "recovery", "dividend", "bonus",
}

NEGATIVE_WORDS = {
    "sell", "bearish", "loss", "crash", "decline", "downgrade", "underperform",
    "miss", "weak", "negative", "fall", "low", "contraction", "downside",
    "fraud", "scam", "penalty", "ban", "debt", "default", "warning", "cuts",
}


def _sentiment_score(text: str) -> float:
    """Simple keyword-based sentiment score [-1, 1]."""
    words = set(text.lower().split())
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.5
    return round(pos / total, 2)


def analyze(symbol: str, company_name: str = "") -> Dict[str, Any]:
    """Analyze news sentiment for a stock."""
    try:
        query = company_name or symbol
        articles = scrape_news(query)

        if not articles:
            return {
                "score": 50, "signal": "HOLD",
                "articles_count": 0, "sentiment_score": 0.5,
                "theme": "No recent news found",
                "verdict": "Insufficient news data for sentiment analysis",
                "chip_label": f"Sentiment: No news",
            }

        # Score all articles
        sentiments = []
        themes = []
        for article in articles:
            text = f"{article.get('title', '')} {article.get('summary', '')}"
            s = _sentiment_score(text)
            sentiments.append(s)
            if article.get("title"):
                themes.append(article["title"][:60])

        avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0.5

        # Convert to 0-100 score
        score = int(avg_sentiment * 100)
        score = max(0, min(100, score))

        if score >= 60:
            signal = "BUY"
        elif score <= 40:
            signal = "SELL"
        else:
            signal = "HOLD"

        # Top theme
        top_theme = themes[0] if themes else "No specific theme"

        # Verdict
        positive_pct = int(avg_sentiment * 100)
        if score >= 70:
            verdict = f"Overwhelmingly positive coverage ({positive_pct}% positive)"
        elif score >= 55:
            verdict = f"Generally positive sentiment ({positive_pct}% positive)"
        elif score >= 45:
            verdict = f"Mixed media sentiment ({positive_pct}% positive)"
        elif score >= 30:
            verdict = f"Negative media tone ({positive_pct}% positive)"
        else:
            verdict = f"Strongly negative coverage ({positive_pct}% positive)"

        # Chip
        if score >= 60:
            chip = f"Sentiment: {positive_pct}% Positive"
        elif score <= 40:
            chip = f"Sentiment: {100 - positive_pct}% Negative"
        else:
            chip = f"Sentiment: {positive_pct}% Mixed"

        return {
            "score": score,
            "signal": signal,
            "articles_count": len(articles),
            "sentiment_score": avg_sentiment,
            "theme": top_theme,
            "verdict": verdict,
            "chip_label": chip,
        }

    except Exception as e:
        logger.error(f"Sentiment analysis error for {symbol}: {e}")
        return {
            "score": 50, "signal": "HOLD",
            "articles_count": 0, "sentiment_score": 0.5,
            "theme": "Analysis error",
            "verdict": "Unable to analyze sentiment",
            "chip_label": "Sentiment: Unavailable",
        }
