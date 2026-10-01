import os
import joblib
import numpy as np
from backend.services.preprocessing import clean_text, get_text_statistics

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")

# Cache in-memory to avoid reloading on every request
_cached_classifier = None
_cached_vectorizer = None
_last_loaded_mtime = 0

def load_model_and_vectorizer():
    """
    Loads classifier and TF-IDF vectorizer from disk with cache invalidation
    if model file is updated.
    """
    global _cached_classifier, _cached_vectorizer, _last_loaded_mtime

    if not os.path.exists(CLASSIFIER_PATH) or not os.path.exists(VECTORIZER_PATH):
        raise FileNotFoundError(
            "No trained model found. Please train the model using a labelled dataset before analyzing news."
        )

    current_mtime = os.path.getmtime(CLASSIFIER_PATH)
    if _cached_classifier is None or _cached_vectorizer is None or current_mtime > _last_loaded_mtime:
        _cached_classifier = joblib.load(CLASSIFIER_PATH)
        _cached_vectorizer = joblib.load(VECTORIZER_PATH)
        _last_loaded_mtime = current_mtime

    return _cached_classifier, _cached_vectorizer

def predict_news_authenticity(news_text: str) -> dict:
    """
    Analyzes an input news article and returns the ML classification result
    along with dynamic confidence probability.
    """
    if not news_text or not news_text.strip():
        raise ValueError("Please enter or upload news content before analyzing.")

    raw_text = news_text.strip()
    if len(raw_text) < 15:
        raise ValueError("The provided news text is too short to analyze. Please provide at least a complete sentence.")

    # 1. Check & load model
    classifier, vectorizer = load_model_and_vectorizer()

    # 2. Text preprocessing with NLTK
    cleaned = clean_text(raw_text)
    if not cleaned.strip():
        # Fallback to lowercased text if cleaned result became empty (e.g. only stopwords)
        cleaned = raw_text.lower()

    # 3. TF-IDF feature transformation
    tfidf_features = vectorizer.transform([cleaned])

    # 4. Model Prediction
    predicted_label = classifier.predict(tfidf_features)[0]

    # 5. Prediction Probability (Confidence Score)
    classes = list(classifier.classes_)
    probabilities = classifier.predict_proba(tfidf_features)[0]

    prob_dict = {}
    for cls_name, prob in zip(classes, probabilities):
        prob_dict[cls_name] = round(float(prob) * 100, 2)

    # Confidence is the probability of the predicted class
    predicted_idx = classes.index(predicted_label)
    confidence_val = float(probabilities[predicted_idx])
    confidence_percentage = round(confidence_val * 100, 2)

    # 6. Text statistics
    stats = get_text_statistics(raw_text, cleaned)

    return {
        "prediction": str(predicted_label).upper(),
        "confidence": confidence_percentage,
        "confidence_ratio": round(confidence_val, 4),
        "probabilities": prob_dict,
        "details": {
            "model_algorithm": "Logistic Regression",
            "feature_extractor": "TF-IDF Vectorizer",
            "raw_word_count": stats["raw_word_count"],
            "cleaned_token_count": stats["cleaned_token_count"],
            "cleaned_preview": cleaned[:120] + ("..." if len(cleaned) > 120 else "")
        }
    }
