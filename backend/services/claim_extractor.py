import re
import string
from collections import Counter
from backend.services.preprocessing import clean_text, STOPWORDS

# Common entity title words to ignore
COMMON_TITLE_WORDS = {
    "The", "A", "An", "In", "On", "At", "By", "For", "With", "About", "Against",
    "Between", "Into", "Through", "During", "Before", "After", "Above", "Below",
    "From", "Up", "Down", "Of", "Off", "Over", "Under", "Again", "Further", "Then",
    "Once", "Here", "There", "When", "Where", "Why", "How", "All", "Any", "Both",
    "Each", "Few", "More", "Most", "Other", "Some", "Such", "No", "Nor", "Not",
    "Only", "Own", "Same", "So", "Than", "Too", "Very", "Can", "Will", "Just",
    "Should", "Now", "Breaking", "Exclusive", "Alert", "Report", "Update", "Video"
}

def extract_entities_and_claims(text: str) -> dict:
    """
    Analyzes raw news text to extract:
    1. Named entities (People, Organizations, Locations)
    2. Temporal markers (Dates, Years)
    3. Core claim keywords & phrases
    4. Search queries for cross-referencing live sources
    """
    if not text or not text.strip():
        return {
            "entities": [],
            "dates": [],
            "keywords": [],
            "claims": [],
            "search_queries": []
        }

    raw = text.strip()

    # 1. Extract dates / temporal references
    date_patterns = [
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s+\d{4})?\b',
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b',
        r'\b(?:19|20)\d{2}\b',
        r'\b(?:yesterday|today|last week|this week|on Monday|on Tuesday|on Wednesday|on Thursday|on Friday|on Saturday|on Sunday)\b'
    ]
    detected_dates = []
    for dp in date_patterns:
        matches = re.findall(dp, raw, re.IGNORECASE)
        for m in matches:
            if m not in detected_dates:
                detected_dates.append(m)

    # 2. Extract Named Entities (Title-cased multi-word phrases and proper nouns)
    # E.g. "Federal Reserve", "White House", "Donald Trump", "Joe Biden", "World Health Organization"
    entity_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
    multi_word_entities = re.findall(entity_pattern, raw)

    # Single-word proper nouns
    single_word_pattern = r'\b[A-Z][a-z]{2,}\b'
    all_capitalized = re.findall(single_word_pattern, raw)

    # Filter out common sentence starters
    clean_entities = []
    for ent in multi_word_entities:
        words = ent.split()
        if words[0] in COMMON_TITLE_WORDS and len(words) > 1:
            ent = " ".join(words[1:])
        if ent and ent not in clean_entities and len(ent) > 3:
            clean_entities.append(ent)

    # Add strong standalone capitalized entities
    capitalized_counts = Counter([
        w for w in all_capitalized 
        if w not in COMMON_TITLE_WORDS and len(w) > 3
    ])
    for w, count in capitalized_counts.most_common(6):
        if not any(w in ent for ent in clean_entities) and w not in clean_entities:
            clean_entities.append(w)

    # 3. Extract core keywords using frequency of cleaned tokens
    cleaned = clean_text(raw)
    tokens = [w for w in cleaned.split() if len(w) > 3 and w not in STOPWORDS]
    word_freq = Counter(tokens)
    top_keywords = [w for w, _ in word_freq.most_common(8)]

    # 4. Extract Key Claim sentences
    sentences = re.split(r'[.!?]+', raw)
    claim_sentences = []
    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) > 20 and len(s_clean) < 220:
            # Check if sentence contains detected entities or top keywords
            has_entity = any(e.lower() in s_clean.lower() for e in clean_entities)
            has_kw = any(k in s_clean.lower() for k in top_keywords[:4])
            if has_entity or has_kw:
                claim_sentences.append(s_clean)

    # Limit claims
    claims = claim_sentences[:3] if claim_sentences else [raw[:150]]

    # 5. Formulate targeted search queries for live cross-referencing
    search_queries = []
    # Query 1: Top entities combined
    if len(clean_entities) >= 2:
        search_queries.append(" ".join(clean_entities[:2]))
    elif len(clean_entities) == 1:
        search_queries.append(clean_entities[0])

    # Query 2: Entities + top keywords
    if clean_entities and top_keywords:
        search_queries.append(f"{clean_entities[0]} {' '.join(top_keywords[:2])}")

    # Query 3: Top keywords alone
    if len(top_keywords) >= 3:
        search_queries.append(" ".join(top_keywords[:3]))

    return {
        "entities": clean_entities[:6],
        "dates": detected_dates[:4],
        "keywords": top_keywords,
        "claims": claims,
        "search_queries": search_queries[:3]
    }
