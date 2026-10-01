import re
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from backend.config import (
    NEWS_API_KEY,
    FACT_CHECK_API_KEY,
    ENABLE_LIVE_FEEDS,
    CONFIGURED_FEEDS
)
from backend.database import (
    insert_news_article,
    insert_verified_training_record,
    get_recent_articles
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FakeNewsDetector/2.0 ResearchBot"
}

def clean_html(raw_html: str) -> str:
    """Strips HTML tags and unescapes entities."""
    if not raw_html:
        return ""
    clean = re.sub(r'<.*?>', '', raw_html)
    return html.unescape(clean).strip()

def parse_date(date_str: str) -> str:
    """Parses various RSS date formats to standardized ISO format."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    try:
        # Fallback ISO parse
        clean_date = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_date)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def extract_fact_check_verdict(title: str, description: str) -> str:
    """
    Examines fact-check headline/description to identify verified labels (REAL / FAKE).
    Strictly accepts only explicit fact-check verdict signals.
    """
    combined = f"{title} {description}".lower()

    fake_indicators = [
        "pants on fire", "false", "mostly false", "fake", "hoax", 
        "untrue", "debunked", "misleading", "fabricated", "incorrect",
        "conspiracy", "altered video", "doctored"
    ]
    real_indicators = [
        "true", "mostly true", "correct", "verified true", "accurate", "factual"
    ]

    for ind in fake_indicators:
        if re.search(r'\b' + re.escape(ind) + r'\b', combined):
            return "FAKE"

    for ind in real_indicators:
        if re.search(r'\b' + re.escape(ind) + r'\b', combined):
            return "REAL"

    return None

def parse_rss_items(raw_text: str) -> list:
    """
    Extracts RSS and Atom items using resilient regex parsing.
    Handles CDATA sections, HTML entities, and avoids XML namespace/prefix errors.
    """
    items = []
    # Match <item>...</item> or <entry>...</entry>
    raw_blocks = re.findall(r'<(item|entry)[\s>](.*?)</\1>', raw_text, re.DOTALL | re.IGNORECASE)

    for _, block in raw_blocks:
        def extract_tag_value(tag_name):
            # Extract content of tag, handling optional attributes
            m = re.search(rf'<{tag_name}(?:\s[^>]*)?>(.*?)</{tag_name}>', block, re.DOTALL | re.IGNORECASE)
            if not m:
                # Also check self-closing link tags like <link href="..." />
                if tag_name == 'link':
                    href_m = re.search(r'<link(?:\s[^>]*)?\shref=["\']([^"\']+)["\']', block, re.IGNORECASE)
                    if href_m:
                        return href_m.group(1).strip()
                return ''
            val = m.group(1).strip()
            # Unwrap CDATA if present
            cdata_match = re.search(r'<!\[CDATA\[(.*?)\]\]>', val, re.DOTALL)
            if cdata_match:
                val = cdata_match.group(1)
            return html.unescape(val).strip()

        title = clean_html(extract_tag_value('title'))
        link = extract_tag_value('link')
        desc = clean_html(extract_tag_value('description') or extract_tag_value('summary') or extract_tag_value('content'))
        pubdate = extract_tag_value('pubDate') or extract_tag_value('published') or extract_tag_value('updated')

        if title:
            items.append({
                'title': title,
                'link': link,
                'desc': desc,
                'pubDate': pubdate
            })

    return items

def fetch_rss_feed(feed_config: dict) -> list:
    """
    Fetches and parses a single RSS news or fact-check feed.
    Returns a list of standardized article dicts.
    """
    feed_url = feed_config["url"]
    source_name = feed_config["name"]
    is_fact_checker = feed_config.get("is_fact_checker", False)

    articles = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []

        parsed_items = parse_rss_items(resp.text)

        for item in parsed_items[:25]:  # Limit per feed
            title = item['title']
            url = item['link']
            desc = item['desc']
            pub_date = parse_date(item['pubDate'])

            article = {
                "title": title,
                "content": desc,
                "source": source_name,
                "url": url.strip(),
                "published_at": pub_date,
                "is_fact_check": is_fact_checker
            }

            articles.append(article)

            # Store in local database avoiding duplicates
            inserted = insert_news_article(
                title=article["title"],
                content=article["content"],
                source=article["source"],
                url=article["url"],
                published_at=article["published_at"]
            )

            # Continuous Learning Hook:
            # If this is a verified fact-check with an explicit label, store in verified_training_data!
            if is_fact_checker and inserted:
                verdict = extract_fact_check_verdict(article["title"], article["content"])
                if verdict in ["REAL", "FAKE"]:
                    insert_verified_training_record(
                        text=f"{article['title']} - {article['content']}",
                        label=verdict,
                        source=source_name,
                        source_url=article["url"]
                    )

    except Exception as e:
        print(f"[NewsFetcher] Warning: failed to fetch feed '{source_name}': {e}")

    return articles


def fetch_from_news_api() -> list:
    """
    Fetches top headlines if NEWS_API_KEY is configured in .env.
    """
    if not NEWS_API_KEY:
        return []

    articles = []
    try:
        url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=30&apiKey={NEWS_API_KEY}"
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            for a in data.get("articles", []):
                title = clean_html(a.get("title", ""))
                url = a.get("url", "")
                content = clean_html(a.get("description", "") or a.get("content", ""))
                source = a.get("source", {}).get("name", "NewsAPI")
                pub_date = parse_date(a.get("publishedAt", ""))

                if title:
                    art = {
                        "title": title,
                        "content": content,
                        "source": source,
                        "url": url,
                        "published_at": pub_date,
                        "is_fact_check": False
                    }
                    articles.append(art)
                    insert_news_article(title, content, source, url, pub_date)
    except Exception as e:
        print(f"[NewsFetcher] NewsAPI fetch error: {e}")

    return articles

def update_all_live_news() -> dict:
    """
    Executes a complete collection run across all configured feeds and APIs.
    Returns status summary with article counts.
    """
    collected_articles = []

    # 1. Fetch from configured feeds
    if ENABLE_LIVE_FEEDS:
        for feed in CONFIGURED_FEEDS:
            arts = fetch_rss_feed(feed)
            collected_articles.extend(arts)

    # 2. Fetch from NewsAPI if key configured
    api_arts = fetch_from_news_api()
    collected_articles.extend(api_arts)

    # Retrieve most recent stored articles from database
    recent = get_recent_articles(limit=30)

    return {
        "success": True,
        "articles_collected_this_run": len(collected_articles),
        "total_active_articles": len(recent),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_live_news(limit: int = 30) -> list:
    """
    Returns current live news articles from database.
    If database has fewer than 5 articles and live feeds are enabled,
    triggers an automatic fetch first.
    """
    articles = get_recent_articles(limit=limit)
    if len(articles) < 5 and ENABLE_LIVE_FEEDS:
        update_all_live_news()
        articles = get_recent_articles(limit=limit)
    return articles
