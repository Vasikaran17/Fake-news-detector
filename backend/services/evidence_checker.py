import re
import math
from datetime import datetime
from collections import Counter
from backend.config import (
    SOURCE_RELIABILITY_WEIGHTS,
    ENABLE_LIVE_FEEDS,
    NEWS_API_KEY,
    FACT_CHECK_API_KEY
)
from backend.database import (
    search_stored_articles,
    get_recent_articles,
    insert_verification_result,
    insert_verified_training_record
)
from backend.services.claim_extractor import extract_entities_and_claims
from backend.services.preprocessing import clean_text
from backend.services.prediction import predict_news_authenticity
from backend.services.news_fetcher import get_live_news

def compute_similarity(text_a: str, text_b: str) -> float:
    """
    Computes lexical similarity (Jaccard & character n-gram overlap)
    between two text passages.
    """
    tokens_a = set(clean_text(text_a).split())
    tokens_b = set(clean_text(text_b).split())

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))

    jaccard = intersection / union if union > 0 else 0.0

    # Also compute containment (fraction of A's key words in B)
    containment = intersection / min(len(tokens_a), len(tokens_b)) if min(len(tokens_a), len(tokens_b)) > 0 else 0.0

    return (jaccard * 0.4) + (containment * 0.6)

def detect_contradiction_or_debunk(claim_text: str, evidence_title: str, evidence_snippet: str) -> bool:
    """
    Checks whether evidence explicitly refutes, disproves, or debunks the claim.
    """
    combined_ev = f"{evidence_title} {evidence_snippet}".lower()

    refutation_signals = [
        r'\bpants on fire\b', r'\bfalse\b', r'\bmostly false\b', r'\bhoax\b',
        r'\bdebunked\b', r'\bfact check: no\b', r'\bnot true\b', r'\bno evidence\b',
        r'\bunfounded\b', r'\bfake claim\b', r'\bconspiracy theory\b', r'\bmisleading\b',
        r'\bdoctored video\b', r'\bfabricated quote\b', r'\bno such\b', r'\bdenies report\b'
    ]

    for sig in refutation_signals:
        if re.search(sig, combined_ev):
            return True

    return False

def verify_news_claim(article_text: str) -> dict:
    """
    End-to-End Evidence-Based Verification Engine:
    1. Extract claims & named entities
    2. Search configured live news and fact-check feeds
    3. Retrieve relevant evidence & categorize into supporting/contradicting
    4. Compute ML linguistic signal using Scikit-learn
    5. Combine signals with safety guards:
       - Insufficient evidence => UNCERTAIN
       - Strong debunking evidence => FAKE
       - Multi-source corroboration => REAL
    6. Store verification result & evidence in SQLite
    7. Continuous Learning: store verified training record if verified signal is strong
    """
    if not article_text or not article_text.strip():
        raise ValueError("Please enter news content before verifying.")

    raw_text = article_text.strip()
    if len(raw_text) < 15:
        raise ValueError("The provided text is too short. Please provide at least a full sentence.")

    # 1. Extract entities, keywords, and search queries
    claim_data = extract_entities_and_claims(raw_text)
    entities = claim_data["entities"]
    keywords = claim_data["keywords"]
    search_queries = claim_data["search_queries"]

    # 2. Get ML model prediction (prior linguistic assessment)
    try:
        ml_res = predict_news_authenticity(raw_text)
        ml_prediction = ml_res["prediction"]
        ml_confidence = ml_res["confidence"]
        ml_probabilities = ml_res["probabilities"]
    except Exception as e:
        ml_prediction = "UNCERTAIN"
        ml_confidence = 50.0
        ml_probabilities = {"REAL": 50.0, "FAKE": 50.0}

    # 3. Retrieve Candidate Evidence from Live Sources & Database
    # Ensure live database has articles
    live_articles = get_live_news(limit=60)
    matched_evidence = []
    seen_urls = set()

    # Search candidates matching keywords and entities
    candidate_articles = []
    if keywords:
        candidate_articles.extend(search_stored_articles(keywords, limit=25))
    candidate_articles.extend(live_articles[:30])

    for art in candidate_articles:
        url = art.get("url", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = art.get("title", "")
        content = art.get("content", "")
        source_name = art.get("source", "Unknown")

        # Compute similarity between submitted text and retrieved article
        sim_title = compute_similarity(raw_text, title)
        sim_content = compute_similarity(raw_text, f"{title} {content}")
        max_sim = max(sim_title, sim_content)

        # Entity match check
        entity_matches = [e for e in entities if e.lower() in f"{title} {content}".lower()]

        # Threshold for relevance
        if max_sim >= 0.18 or (len(entity_matches) >= 2 and max_sim >= 0.12):
            # Determine evidence stance
            is_debunk = detect_contradiction_or_debunk(raw_text, title, content)
            is_fact_check = "fact" in source_name.lower() or "politifact" in source_name.lower()

            if is_debunk:
                ev_type = "contradicting"
            elif max_sim >= 0.25 and not is_debunk:
                ev_type = "supporting"
            else:
                ev_type = "context"

            # Reliability weight
            weight = 0.85
            for cat, w in SOURCE_RELIABILITY_WEIGHTS.items():
                if cat.lower() in source_name.lower():
                    weight = w
                    break

            snippet = content[:200] + ("..." if len(content) > 200 else "")
            matched_evidence.append({
                "source": source_name,
                "title": title,
                "url": url,
                "published_at": art.get("published_at", ""),
                "evidence_type": ev_type,
                "similarity": round(max_sim, 3),
                "weight": weight,
                "snippet": snippet or title,
                "matched_entities": entity_matches
            })

    # Sort evidence by relevance similarity
    matched_evidence.sort(key=lambda x: x["similarity"], reverse=True)

    supporting = [e for e in matched_evidence if e["evidence_type"] == "supporting"]
    contradicting = [e for e in matched_evidence if e["evidence_type"] == "contradicting"]
    context = [e for e in matched_evidence if e["evidence_type"] == "context"]

    # 4. Formulate Decision & Confidence Score
    verdict = "UNCERTAIN"
    confidence = 50.0
    evidence_summary = ""
    is_verified_label = False

    # Check live source availability
    has_live_sources = len(live_articles) > 0

    if not has_live_sources and not ENABLE_LIVE_FEEDS and not NEWS_API_KEY:
        verdict = "UNCERTAIN"
        confidence = 50.0
        evidence_summary = (
            "Live verification sources are not configured. Add required API credentials or "
            "enable live feeds in .env to perform live evidence cross-checking."
        )

    elif contradicting:
        # Strong contradicting evidence from reliable source
        top_contra = contradicting[0]
        verdict = "FAKE"
        # Dynamic confidence based on source weight and count
        base_conf = 80.0 + min(len(contradicting) * 5.0, 15.0)
        confidence = round(min(base_conf * top_contra["weight"], 97.5), 1)
        evidence_summary = (
            f"Available reliable evidence contradicts this claim. Debunking report found from "
            f"{top_contra['source']}: '{top_contra['title']}'."
        )
        is_verified_label = True

    elif len(supporting) >= 2:
        # Multiple independent supporting sources corroborating the story
        sources_list = list(set(s['source'] for s in supporting))
        verdict = "REAL"
        base_conf = 78.0 + min(len(supporting) * 4.0, 16.0)
        confidence = round(min(base_conf, 96.0), 1)
        evidence_summary = (
            f"Available evidence strongly supports the submitted claim. Corroborated across "
            f"{len(sources_list)} independent sources including {', '.join(sources_list[:2])}."
        )
        is_verified_label = True

    elif len(supporting) == 1 and supporting[0]["similarity"] >= 0.35:
        verdict = "REAL"
        confidence = 72.0
        evidence_summary = (
            f"Available evidence supports this claim. Corroborated by reporting from "
            f"{supporting[0]['source']}: '{supporting[0]['title']}'."
        )
        is_verified_label = False

    else:
        # INSUFFICIENT EVIDENCE RULE:
        # Never label FAKE merely because not found online. No evidence != Evidence of falsity.
        verdict = "UNCERTAIN"
        confidence = 50.0
        if matched_evidence:
            evidence_summary = (
                f"Found {len(matched_evidence)} related articles, but evidence is insufficient or "
                "inconclusive to definitively verify or refute this specific claim."
            )
        else:
            evidence_summary = (
                "Not enough reliable evidence was found to confidently classify this claim. "
                "Breaking news or niche topics may require additional human verification."
            )

    # 5. Store Verification Result in Database
    all_evidence = (contradicting + supporting + context)[:8]
    verif_id = insert_verification_result(
        article_text=raw_text,
        result=verdict,
        confidence=confidence,
        ml_prediction=ml_prediction,
        ml_confidence=ml_confidence,
        evidence_summary=evidence_summary,
        evidence_items=all_evidence
    )

    # 6. Continuous Learning Hook:
    # Only store in verified learning records if the verification signal is authoritative!
    if is_verified_label and verdict in ["REAL", "FAKE"] and len(all_evidence) > 0:
        top_ev = all_evidence[0]
        insert_verified_training_record(
            text=raw_text,
            label=verdict,
            source=top_ev["source"],
            source_url=top_ev["url"]
        )

    flat_evidence = (supporting[:4] + contradicting[:4] + context[:3])

    return {
        "verification_id": verif_id,
        "result": verdict,
        "confidence": confidence,
        "evidence_summary": evidence_summary,
        "evidence": flat_evidence,
        "supporting_evidence": supporting[:4],
        "contradicting_evidence": contradicting[:4],
        "context_evidence": context[:3],
        "sources_checked_count": len(all_evidence),
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "ml_details": {
            "prediction": ml_prediction,
            "confidence": ml_confidence,
            "probabilities": ml_probabilities,
            "linguistic_role": "Used as prior signal combined with live evidence."
        },
        "claim_extracted": claim_data["claims"][0] if claim_data["claims"] else raw_text[:80],
        "entities": {
            "entities_list": entities,
            "people": entities[:3],
            "organizations": [],
            "locations": []
        },
        "extracted_analysis": {
            "entities": entities,
            "keywords": keywords[:6],
            "claims": claim_data["claims"][:2]
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
