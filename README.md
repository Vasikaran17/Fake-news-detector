# Fake News Detector — Live & Continuously Updated System

> **"Verify information before you share it."**  
> An NLP, Machine Learning, and Evidence-Based Verification System combining real-time journalism feeds, fact-checking sources, and safe continuous learning.

---

## 1. Project Overview

The **Fake News Detector** has been upgraded from a manual training prototype into a **Live, Evidence-Based, Continuously Updated Fake News Verification System**.

In traditional machine learning setups, users are required to manually curate and upload CSV datasets to train a classifier. Furthermore, static machine learning classifiers cannot evaluate emerging real-world events because they lack real-time context.

This system resolves both limitations:
1. **Zero Manual Training Required for End Users**: The system comes pre-trained with a high-accuracy baseline model (98.14% accuracy on 34,000+ benchmark articles) and continuously ingests real-time journalism and fact-checking feeds.
2. **Evidence-Based Corroboration**: Claims are cross-checked against configured live news organizations (BBC, NPR, Reuters, AP) and authoritative fact-checking feeds (PolitiFact, FactCheck.org).
3. **Safe Continuous Learning**: The system improves its knowledge over time through an automated, safe continuous learning pipeline. Only independently verified fact-check records enter the training dataset—preventing confirmation bias and self-reinforcing errors.

---

## 2. Upgraded Architecture & Workflows

### Verification Workflow

```
User enters news / claim (or uploads .txt)
                    ↓
            Click VERIFY NEWS
                    ↓
         Backend receives article
                    ↓
     Clean text using NLTK preprocessing
                    ↓
Extract important claims & named entities (People, Orgs, Locations, Dates)
                    ↓
     Search configured live / current sources
                    ↓
  Collect supporting, contradicting & contextual evidence
                    ↓
  Compare claim against retrieved source coverage
                    ↓
Synthesize: ML Stylistic Signal + Evidence Agreement + Source Weight
                    ↓
               Determine:
        REAL / FAKE / UNCERTAIN
                    ↓
        Calculate dynamic confidence
                    ↓
Show evidence citations (Source, Headline, Date, URL, Summary)
                    ↓
      Store user analysis in local SQLite database
                    ↓
If verified fact-check information is available:
       Add to verified learning dataset
                    ↓
When threshold is reached (e.g. 50 records):
        Automatically retrain ML model
                    ↓
        Save new model version (v2, v3, ...)
```

---

## 3. Safe Continuous Learning Architecture

### Critical Safeguards

> [!IMPORTANT]
> **Unverified live articles are NOT automatically used as training labels.**  
> A live news article by itself does not provide an authoritative REAL/FAKE label.  
> **The model's own predictions are NEVER used as training labels.**  
> If an AI system labels an article as FAKE and immediately trains on that label, any hallucination or false classification becomes self-reinforcing.

```
LIVE NEWS / FACT-CHECK FEEDS
            ↓
         COLLECT
            ↓
        NORMALIZE (Deduplicate by URL & headline)
            ↓
     EXTRACT CLAIMS
            ↓
CROSS-CHECK WITH RELIABLE SOURCES
            ↓
GENERATE VERIFIED LABEL (Only from authoritative fact-checking bodies)
            ↓
STORE VERIFIED RECORD (SQLite verified_training_data & data/verified_news.csv)
            ↓
CHECK THRESHOLD (if verified_records >= MODEL_UPDATE_THRESHOLD)
            ↓
RETRAIN & EVALUATE (Compare test accuracy against current model)
            ↓
PROMOTE TO NEW VERSION (models/archive/model_v{N} & models/current)
```

---

## 4. Verification Verdicts & Result Types

The system returns one of three evidence-grounded states:

| Status | Color Indicator | Meaning & Criteria |
| :--- | :--- | :--- |
| **REAL** | **Green** | Available reliable evidence supports the claim. Multiple independent sources corroborate the reported events. |
| **FAKE** | **Red** | Available reliable evidence contradicts the claim. Authoritative fact-checking organizations have debunked or refuted the assertion. |
| **UNCERTAIN** | **Orange / Amber** | Available evidence is insufficient or conflicting. **Crucial Rule:** No evidence is *not* automatically evidence of falsity. |

---

## 5. Technology Stack

- **Backend Framework**: Python 3, Flask, Flask-CORS
- **Database**: SQLite (`data/fake_news_detector.db`)
- **Natural Language Processing**: NLTK (Tokenization, stopword removal, entity & keyword extraction)
- **Machine Learning**: Scikit-learn (TF-IDF Vectorizer with unigrams & bigrams, Logistic Regression)
- **Dataset Benchmark**: Kaggle Clément Bisaillon / ISOT dataset (34,107 articles, 98.14% baseline accuracy)
- **Model Serialization & Versioning**: Joblib, versioned under `backend/models/current` and `backend/models/archive`
- **Data Persistence**: CSV (`data/verified_news.csv`) and SQLite
- **Live Feeds & News APIs**: Configurable multi-feed RSS parser and REST APIs with source reliability weighting
- **Frontend**: Responsive HTML5, CSS3, Vanilla JavaScript (Student-designed handmade UI)

---

## 6. Directory Structure

```
FAKE NEWS DETECTOR/
├── backend/
│   ├── app.py                      # Flask application & REST API routes
│   ├── config.py                   # Centralized configuration & environment loader
│   ├── database.py                 # SQLite database schema, helpers & connection pooling
│   ├── train_clement_dataset.py    # Training script for 34k Kaggle dataset
│   ├── models/
│   │   ├── current/                # Active production model, vectorizer & metadata
│   │   └── archive/                # Versioned historical models (model_v1, model_v2, ...)
│   └── services/
│       ├── claim_extractor.py      # Entity extraction, keyword generation, search queries
│       ├── continuous_learning.py  # Safe continuous learning pipeline & automatic retraining
│       ├── evidence_checker.py     # Cross-source corroboration, debunking detection & confidence
│       ├── news_fetcher.py         # Multi-source live news & fact-check feed collector
│       ├── preprocessing.py        # NLTK text normalization and tokenization
│       └── prediction.py           # ML probabilistic classifier
│
├── frontend/
│   ├── index.html                  # Home page with live system status indicator
│   ├── verify.html                 # Primary Verify News page with evidence result card
│   ├── live.html                   # Live News page with latest dispatches & Verify buttons
│   ├── history.html                # User analysis history with REAL/FAKE/UNCERTAIN filters
│   ├── about.html                  # Architecture, pipeline diagram, and viva defense guide
│   ├── train.html                  # Developer/Admin manual retraining utility
│   ├── css/
│   │   └── style.css               # Clean student-designed styles, badges, and evidence cards
│   └── js/
│       ├── main.js                 # Global status polling & mobile navigation
│       ├── verify.js               # News verification request & dynamic evidence rendering
│       ├── live.js                 # Live news feed loader and feed refresher
│       └── history.js              # History retrieval, filtering, and re-verification
│
├── data/
│   ├── fake_news_detector.db       # SQLite local database
│   └── verified_news.csv           # Continuous learning verified records
│
├── sample_dataset/                 # Kaggle Clément Bisaillon benchmark files
│   ├── clement_bisaillon_dataset.csv
│   ├── test_real_article.txt
│   └── test_fake_article.txt
│
├── .env.example                    # Template for environment configuration
├── .env                            # Local configuration (never committed to Git)
├── requirements.txt                # Python dependencies
└── README.md                       # Comprehensive documentation
```

---

## 7. Configuration & Environment Variables

Create or update the `.env` file in the project root:

```env
# Server Configuration
PORT=5000
DEBUG=False
SECRET_KEY=change-this-in-production

# External Live News & Fact-Check APIs (Optional)
NEWS_API_KEY=
FACT_CHECK_API_KEY=

# Continuous Learning Thresholds
MODEL_UPDATE_THRESHOLD=50
MIN_ACCURACY_THRESHOLD=0.85
NEWS_FETCH_INTERVAL_MINUTES=60
```

> [!NOTE]
> Even without external commercial API keys, the system includes built-in live RSS parsers for major journalism outlets (BBC, NPR, Reuters) and fact-check feeds (PolitiFact, FactCheck.org) that work out of the box.

---

## 8. Database Architecture (SQLite)

The system automatically initializes `data/fake_news_detector.db` with five core tables:

1. **`news_articles`**: Stores ingested live articles (title, content, source, url, published_at, collected_at).
2. **`verification_results`**: Records each user analysis (article_text, result, confidence, created_at).
3. **`evidence`**: Links verification records to citations (source, title, url, published_at, evidence_type, summary, similarity).
4. **`verified_training_data`**: Stores corroborated fact-check records for model retraining (text, label, source, source_url, verified_at, confidence).
5. **`model_versions`**: Audits all trained model iterations (version, trained_at, training_records, accuracy, precision, recall, f1_score).

---

## 9. API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/system-status` | `GET` | Returns live system status, model version, and verified record count |
| `/api/live-news` | `GET` | Returns currently ingested live news and fact-check articles |
| `/api/verify` | `POST` | Verifies a submitted text claim against live sources and ML prior |
| `/api/verify-file` | `POST` | Verifies an uploaded plain text (`.txt`) file |
| `/api/history` | `GET` | Retrieves real user verification history from the database |
| `/api/evidence/<id>` | `GET` | Retrieves detailed evidence breakdown for a past analysis |
| `/api/learning-status` | `GET` | Returns continuous learning metrics and retraining threshold status |
| `/api/update-news` | `POST` | Triggers immediate on-demand news collection and deduplication |
| `/api/model-status` | `GET` | Returns current model metadata, version, and performance metrics |

---

## 10. Running the Application

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server
```bash
python backend/app.py
```
The server will start at `http://127.0.0.1:5000`.

### 3. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 11. Demonstration Flow for College Presentation

When presenting this project to evaluators:

1. **Home Page (`/`)**:
   - Point out the **LIVE VERIFICATION SYSTEM** indicator and dynamic last update timestamp.
   - Show the live data metrics: Articles checked, verified records, current model version (`v1.0`).
2. **Live News Page (`/live`)**:
   - Show real news articles collected from configured feeds (BBC, NPR, etc.).
   - Click the **"Verify Claim"** button beside any article to transfer it directly into the verification workspace.
3. **Verify News Page (`/verify`)**:
   - Paste a claim or click an example.
   - Click **VERIFY NEWS** and observe the loading indicator.
   - Review the **Evidence-Based Result Card**:
     - Status: **REAL**, **FAKE**, or **UNCERTAIN**.
     - Dynamic confidence percentage.
     - **"Why?" Evidence Breakdown**: Show the supporting and contradicting citations with source names, dates, and direct links.
     - Highlight the limitation message: *"Automated verification is an assistive tool, not a guarantee of truth."*
4. **Analysis History Page (`/history`)**:
   - Demonstrate that the query was saved into the local SQLite database.
   - Filter by **REAL**, **FAKE**, or **UNCERTAIN**.
   - Click **Re-verify** to re-examine a past claim.
5. **About Page (`/about`)**:
   - Walk through the 9-step pipeline flowchart.
   - Explain the viva concept: **Why we never train on unverified live news or model predictions** to prevent confirmation bias loops.

---

## 12. Security & Privacy Considerations

- **API Key Protection**: API keys are loaded via `.env` using `python-dotenv` and are never exposed to clientside JavaScript.
- **Input Sanitization**: All user input and RSS feed titles are escaped to prevent XSS.
- **Upload Validation**: File uploads are restricted to `.txt` files under 1.5 GB. Files are read in memory/temporary staging and never executed.
- **Duplicate Prevention**: URL hashing and normalized title matching prevent repetitive database pollution.
- **Graceful Degradation**: If external feeds are unreachable, the system returns `UNCERTAIN` with a clear explanation rather than crashing or guessing.
