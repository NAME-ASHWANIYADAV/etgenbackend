"""
News scraper service — fetches financial news from RSS feeds.
Fully synchronous — no async.
"""
import feedparser
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
]


def scrape_news(query: str) -> List[Dict[str, Any]]:
    """Fetch recent news articles matching the query. Fully synchronous."""
    articles = []
    search_terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 2]

    # RSS feeds
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                combined = f"{title} {summary}".lower()

                if any(term in combined for term in search_terms):
                    articles.append({
                        "title": title,
                        "summary": summary[:200],
                        "source": "ET Markets",
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                    })
        except Exception as e:
            logger.error(f"RSS feed error: {e}")

    # Google News RSS backup
    try:
        google_rss = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-IN&gl=IN"
        feed = feedparser.parse(google_rss)
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:200],
                "source": "Google News",
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
    except Exception as e:
        logger.error(f"Google News RSS error: {e}")

    return articles[:10]
