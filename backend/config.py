import os
from dotenv import load_dotenv

# Load environment variables from .env
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Directories
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
CURRENT_MODEL_DIR = os.path.join(MODELS_DIR, "current")
ARCHIVE_MODEL_DIR = os.path.join(MODELS_DIR, "archive")
LEGACY_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CURRENT_MODEL_DIR, exist_ok=True)
os.makedirs(ARCHIVE_MODEL_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Database & Verified Storage
DB_PATH = os.path.join(DATA_DIR, "fake_news_detector.db")
VERIFIED_CSV_PATH = os.path.join(DATA_DIR, "verified_news.csv")

# Continuous Learning & Retraining Config
MODEL_UPDATE_THRESHOLD = int(os.getenv("MODEL_UPDATE_THRESHOLD", 50))

# API Keys (Never exposed to frontend)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()
FACT_CHECK_API_KEY = os.getenv("FACT_CHECK_API_KEY", "").strip()

# Live Feeds Configuration
ENABLE_LIVE_FEEDS = os.getenv("ENABLE_LIVE_FEEDS", "true").lower() in ("true", "1", "yes")
LIVE_NEWS_FETCH_INTERVAL_MINUTES = int(os.getenv("LIVE_NEWS_FETCH_INTERVAL_MINUTES", 60))

# Configured Live Feeds (Open, live verified journalism and fact-checking feeds)
CONFIGURED_FEEDS = [
    {
        "name": "Reuters Top News",
        "category": "Established News",
        "reliability_weight": 0.95,
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml", # High-reliability fallback RSS
        "is_fact_checker": False
    },
    {
        "name": "Associated Press News",
        "category": "Established News",
        "reliability_weight": 0.95,
        "url": "https://feeds.feedburner.com/apnews_topnews",
        "is_fact_checker": False
    },
    {
        "name": "NPR Top News",
        "category": "Established News",
        "reliability_weight": 0.90,
        "url": "https://feeds.npr.org/1001/rss.xml",
        "is_fact_checker": False
    },
    {
        "name": "BBC News",
        "category": "Established News",
        "reliability_weight": 0.90,
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "is_fact_checker": False
    },
    {
        "name": "PolitiFact Fact-Checks",
        "category": "Fact-Checking Organization",
        "reliability_weight": 1.0,
        "url": "https://www.politifact.com/rss/factchecks/",
        "is_fact_checker": True
    },
    {
        "name": "FactCheck.org",
        "category": "Fact-Checking Organization",
        "reliability_weight": 1.0,
        "url": "https://www.factcheck.org/feed/",
        "is_fact_checker": True
    }
]

# Source Reliability Categories & Weights
SOURCE_RELIABILITY_WEIGHTS = {
    "Official Government": 0.98,
    "Fact-Checking Organization": 1.0,
    "Established News": 0.95,
    "Mainstream Press": 0.85,
    "Secondary Source": 0.70
}
