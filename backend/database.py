import os
import sqlite3
import re
from datetime import datetime
from backend.config import DB_PATH

def get_connection():
    """Returns a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the SQLite database and all required tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. news_articles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS news_articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT,
        source TEXT,
        url TEXT UNIQUE,
        published_at TEXT,
        collected_at TEXT
    );
    """)

    # 2. verification_results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_text TEXT NOT NULL,
        result TEXT NOT NULL,
        confidence REAL NOT NULL,
        ml_prediction TEXT,
        ml_confidence REAL,
        evidence_summary TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 3. evidence
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        verification_id INTEGER NOT NULL,
        source TEXT,
        title TEXT,
        url TEXT,
        published_at TEXT,
        evidence_type TEXT,
        snippet TEXT,
        FOREIGN KEY(verification_id) REFERENCES verification_results(id) ON DELETE CASCADE
    );
    """)

    # 4. verified_training_data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verified_training_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        label TEXT NOT NULL,
        source TEXT,
        source_url TEXT,
        verified_at TEXT NOT NULL
    );
    """)

    # 5. model_versions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version TEXT NOT NULL UNIQUE,
        trained_at TEXT NOT NULL,
        training_records INTEGER NOT NULL,
        accuracy REAL,
        precision REAL,
        recall REAL,
        f1_score REAL,
        is_active INTEGER DEFAULT 0
    );
    """)

    # Create indexes for fast lookup
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_url ON news_articles(url);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verif_created ON verification_results(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verif_result ON verification_results(result);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_verif ON evidence(verification_id);")

    conn.commit()
    conn.close()

# -------------------------------------------------------------
# News Article Database Operations
# -------------------------------------------------------------

def normalize_title(title: str) -> str:
    """Normalizes title for duplicate detection."""
    return re.sub(r'\W+', '', title.lower().strip())

def insert_news_article(title: str, content: str, source: str, url: str, published_at: str) -> bool:
    """
    Inserts a news article avoiding duplicates via URL and normalized headline matching.
    Returns True if inserted, False if duplicate.
    """
    if not title or not title.strip():
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 1. URL check
    if url:
        cursor.execute("SELECT id FROM news_articles WHERE url = ?", (url,))
        if cursor.fetchone():
            conn.close()
            return False

    # 2. Normalized headline check on recent articles
    cursor.execute("SELECT title FROM news_articles ORDER BY id DESC LIMIT 500")
    recent = cursor.fetchall()
    norm_new = normalize_title(title)
    for r in recent:
        if normalize_title(r['title']) == norm_new:
            conn.close()
            return False

    collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO news_articles (title, content, source, url, published_at, collected_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title.strip(), (content or "").strip(), source, url, published_at, collected_at))

    conn.commit()
    conn.close()
    return True

def get_recent_articles(limit: int = 30) -> list:
    """Returns the most recent collected news articles."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, content, source, url, published_at, collected_at
        FROM news_articles
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def search_stored_articles(keywords: list, limit: int = 15) -> list:
    """Searches stored articles for given keywords."""
    if not keywords:
        return []
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []
    for kw in keywords[:5]: # Take top 5 keywords
        conditions.append("(title LIKE ? OR content LIKE ?)")
        params.extend([f"%{kw}%", f"%{kw}%"])

    query = f"""
        SELECT id, title, content, source, url, published_at
        FROM news_articles
        WHERE {' OR '.join(conditions)}
        ORDER BY id DESC
        LIMIT ?
    """
    params.append(limit)
    cursor.execute(query, tuple(params))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# -------------------------------------------------------------
# Verification Results & Evidence Operations
# -------------------------------------------------------------

def insert_verification_result(article_text: str, result: str, confidence: float,
                               ml_prediction: str, ml_confidence: float,
                               evidence_summary: str, evidence_items: list) -> int:
    """Stores user verification result and associated evidence items."""
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO verification_results (article_text, result, confidence, ml_prediction, ml_confidence, evidence_summary, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (article_text, result, confidence, ml_prediction, ml_confidence, evidence_summary, created_at))

    verif_id = cursor.lastrowid

    for ev in evidence_items:
        cursor.execute("""
            INSERT INTO evidence (verification_id, source, title, url, published_at, evidence_type, snippet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            verif_id,
            ev.get("source", "Unknown"),
            ev.get("title", ""),
            ev.get("url", ""),
            ev.get("published_at", ""),
            ev.get("evidence_type", "context"),
            ev.get("snippet", "")
        ))

    conn.commit()
    conn.close()
    return verif_id

def get_verification_history(limit: int = 50, filter_result: str = None) -> list:
    """Fetches user verification history with optional result filtering."""
    conn = get_connection()
    cursor = conn.cursor()

    if filter_result and filter_result.upper() in ["REAL", "FAKE", "UNCERTAIN"]:
        cursor.execute("""
            SELECT v.id, v.article_text, v.result, v.confidence, v.ml_prediction,
                   v.evidence_summary, v.created_at, COUNT(e.id) as sources_count
            FROM verification_results v
            LEFT JOIN evidence e ON v.id = e.verification_id
            WHERE v.result = ?
            GROUP BY v.id
            ORDER BY v.id DESC
            LIMIT ?
        """, (filter_result.upper(), limit))
    else:
        cursor.execute("""
            SELECT v.id, v.article_text, v.result, v.confidence, v.ml_prediction,
                   v.evidence_summary, v.created_at, COUNT(e.id) as sources_count
            FROM verification_results v
            LEFT JOIN evidence e ON v.id = e.verification_id
            GROUP BY v.id
            ORDER BY v.id DESC
            LIMIT ?
        """, (limit,))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_evidence_for_verification(verification_id: int) -> list:
    """Fetches evidence items linked to a verification result."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT source, title, url, published_at, evidence_type, snippet
        FROM evidence
        WHERE verification_id = ?
        ORDER BY id ASC
    """, (verification_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# -------------------------------------------------------------
# Verified Training Data (Continuous Learning)
# -------------------------------------------------------------

def insert_verified_training_record(text: str, label: str, source: str, source_url: str) -> bool:
    """
    Inserts a verified record into verified_training_data.
    Safeguard: ONLY verified items with explicit ground truth / fact-check labels enter here!
    """
    if not text or not label or label.upper() not in ["REAL", "FAKE"]:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # Prevent duplicate text in training set
    cursor.execute("SELECT id FROM verified_training_data WHERE text = ?", (text.strip(),))
    if cursor.fetchone():
        conn.close()
        return False

    verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO verified_training_data (text, label, source, source_url, verified_at)
        VALUES (?, ?, ?, ?, ?)
    """, (text.strip(), label.upper(), source, source_url, verified_at))

    conn.commit()
    conn.close()
    return True

def get_verified_data_count() -> int:
    """Returns the total number of verified training records."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM verified_training_data")
    cnt = cursor.fetchone()['cnt']
    conn.close()
    return cnt

def get_all_verified_training_records() -> list:
    """Retrieves all verified training records for model retraining."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT text, label, source, source_url, verified_at FROM verified_training_data")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

# -------------------------------------------------------------
# Model Versions
# -------------------------------------------------------------

def record_model_version(version: str, training_records: int,
                         accuracy: float, precision: float, recall: float, f1_score: float) -> int:
    """Records a new trained model version and sets it active."""
    conn = get_connection()
    cursor = conn.cursor()
    trained_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Set previous versions inactive
    cursor.execute("UPDATE model_versions SET is_active = 0")

    cursor.execute("""
        INSERT INTO model_versions (version, trained_at, training_records, accuracy, precision, recall, f1_score, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (version, trained_at, training_records, accuracy, precision, recall, f1_score))

    vid = cursor.lastrowid
    conn.commit()
    conn.close()
    return vid

def get_active_model_version() -> dict:
    """Returns the currently active model version record."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT version, trained_at, training_records, accuracy, precision, recall, f1_score
        FROM model_versions
        WHERE is_active = 1
        ORDER BY id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# -------------------------------------------------------------
# System Status & Metrics
# -------------------------------------------------------------

def get_system_stats() -> dict:
    """Calculates live system statistics for UI indicators."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
    articles_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM verification_results")
    verifications_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM verified_training_data")
    verified_data_count = cursor.fetchone()['cnt']

    cursor.execute("SELECT MAX(collected_at) as last_update FROM news_articles")
    last_news_row = cursor.fetchone()
    last_update = last_news_row['last_update'] if last_news_row and last_news_row['last_update'] else None

    conn.close()

    active_model = get_active_model_version()
    current_version = active_model["version"] if active_model else "v1.0"
    retrain_threshold = 50
    records_until = max(0, retrain_threshold - (verified_data_count % retrain_threshold))

    return {
        "status": "connected",
        "live_system": "LIVE VERIFICATION SYSTEM",
        "connected": True,
        "articles_checked": articles_count,
        "verifications_performed": verifications_count,
        "verified_records": verified_data_count,
        "last_update": last_update,
        "current_model": current_version,
        "current_model_version": current_version,
        "records_until_retrain": records_until,
        "threshold": retrain_threshold,
        "model_accuracy": active_model["accuracy"] if active_model else None
    }
