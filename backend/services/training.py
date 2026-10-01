import os
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
from backend.services.preprocessing import clean_text

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "model"))
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

def validate_dataset_columns(df: pd.DataFrame):
    """
    Validates that the dataframe contains required 'text' and 'label' columns
    (case-insensitive). Renames them to standard lowercase.
    """
    col_mapping = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if col_lower == 'text' or col_lower == 'news' or col_lower == 'article':
            col_mapping[col] = 'text'
        elif col_lower == 'label' or col_lower == 'class' or col_lower == 'target':
            col_mapping[col] = 'label'

    df.rename(columns=col_mapping, inplace=True)

    if 'text' not in df.columns or 'label' not in df.columns:
        found_cols = ", ".join([f"'{c}'" for c in df.columns])
        raise ValueError(
            f"Dataset must contain 'text' and 'label' columns. Found columns: [{found_cols}]. "
            "Please ensure your CSV header has 'text' and 'label'."
        )

    if len(df) == 0:
        raise ValueError("The uploaded CSV file is empty. Please provide a dataset with news articles.")

    return df

def normalize_labels(series: pd.Series) -> pd.Series:
    """
    Normalizes labels to strictly 'REAL' or 'FAKE'.
    Handles common formats:
    - 'REAL' / 'FAKE' (case insensitive)
    - 1 (REAL) / 0 (FAKE) or 0 (REAL) / 1 (FAKE) if strings
    - 'true' / 'false'
    """
    def map_label(val):
        s = str(val).strip().upper()
        if s in ['REAL', 'TRUE', '1', 'FACTUAL', 'AUTHENTIC', 'GENUINE']:
            return 'REAL'
        elif s in ['FAKE', 'FALSE', '0', 'HOAX', 'MISLEADING', 'UNRELIABLE']:
            return 'FAKE'
        return s

    normalized = series.apply(map_label)
    unique_labels = set(normalized.unique())

    # We need at least both REAL and FAKE in the dataset
    if not ({'REAL', 'FAKE'}.issubset(unique_labels)):
        raise ValueError(
            f"Dataset labels must represent both 'REAL' and 'FAKE' news. "
            f"Detected unique labels: {list(unique_labels)}. "
            "Please check that your CSV label column has both REAL and FAKE examples."
        )

    # Filter out any unexpected third label if dirty data exists
    return normalized

def preview_csv(file_path: str) -> dict:
    """
    Parses and returns dataset preview metadata for datasets up to 1.5 GB.
    Uses chunked reading to calculate row count and label distribution efficiently
    without excessive RAM allocation.
    """
    try:
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

        # For files under 20MB, standard read
        if file_size_mb < 20:
            try:
                df = pd.read_csv(file_path, encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding='latin-1', low_memory=False)

            df = validate_dataset_columns(df)
            df['label'] = normalize_labels(df['label'])

            label_counts = df['label'].value_counts().to_dict()

            return {
                "total_rows": int(len(df)),
                "columns": list(df.columns),
                "file_size_mb": file_size_mb,
                "label_distribution": {
                    "REAL": int(label_counts.get("REAL", 0)),
                    "FAKE": int(label_counts.get("FAKE", 0))
                }
            }
        else:
            # Chunked processing for large datasets (> 20 MB up to 1.5 GB)
            encoding = 'utf-8'
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.readline()
            except UnicodeDecodeError:
                encoding = 'latin-1'

            first_chunk = pd.read_csv(file_path, nrows=5, encoding=encoding, low_memory=False)
            first_chunk = validate_dataset_columns(first_chunk)
            cols = list(first_chunk.columns)

            total_rows = 0
            real_count = 0
            fake_count = 0

            for chunk in pd.read_csv(file_path, chunksize=50000, encoding=encoding, low_memory=False):
                chunk = validate_dataset_columns(chunk)
                norm_labels = normalize_labels(chunk['label'])
                counts = norm_labels.value_counts()
                real_count += int(counts.get("REAL", 0))
                fake_count += int(counts.get("FAKE", 0))
                total_rows += len(chunk)

            return {
                "total_rows": total_rows,
                "columns": cols,
                "file_size_mb": file_size_mb,
                "label_distribution": {
                    "REAL": real_count,
                    "FAKE": fake_count
                }
            }
    except Exception as e:
        raise ValueError(str(e))

def train_fake_news_model(csv_file_path: str) -> dict:
    """
    Executes the complete machine learning training pipeline:
    1. Load and validate CSV (supports large datasets > 600 MB)
    2. Normalize labels to 'REAL' and 'FAKE'
    3. Clean and preprocess news text using NLTK pipeline
    4. Train/Test split
    5. Fit TF-IDF Vectorizer on training data
    6. Fit LogisticRegression classifier (parallelized with n_jobs=-1)
    7. Evaluate model performance (Accuracy, Precision, Recall, F1, Confusion Matrix)
    8. Serialize model & vectorizer using joblib
    9. Save metadata JSON
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    file_size_bytes = os.path.getsize(csv_file_path)
    file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    # 1. Load CSV
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_file_path, encoding='latin-1', low_memory=False)

    # Validate columns
    df = validate_dataset_columns(df)

    # Clean missing values
    df.dropna(subset=['text', 'label'], inplace=True)
    df = df[df['text'].astype(str).str.strip() != '']

    if len(df) < 10:
        raise ValueError("Dataset is too small for machine learning. Please provide at least 10 news articles.")

    # 2. Normalize labels
    df['label'] = normalize_labels(df['label'])
    df = df[df['label'].isin(['REAL', 'FAKE'])]

    total_samples = len(df)
    real_count = int((df['label'] == 'REAL').sum())
    fake_count = int((df['label'] == 'FAKE').sum())

    if real_count < 2 or fake_count < 2:
        raise ValueError("Dataset must contain at least 2 samples for both REAL and FAKE categories.")

    # For massive datasets (> 100,000 articles), sample 100,000 articles (50k REAL, 50k FAKE)
    # for optimal RAM efficiency and training speed
    dataset_sampling_note = None
    if len(df) > 100000:
        dataset_sampling_note = f"Large dataset detected ({total_samples:,} articles). Trained on a balanced stratified sample of 100,000 articles for optimal performance."
        df = df.groupby('label', group_keys=False).apply(
            lambda x: x.sample(min(len(x), 50000), random_state=42)
        )

    # 3. Preprocess text using NLTK pipeline
    df['cleaned_text'] = df['text'].apply(clean_text)

    # Filter out any rows that became completely empty after stopword removal
    valid_df = df[df['cleaned_text'].str.strip() != '']
    if len(valid_df) < 6:
        # Fallback to original text lowercased if preprocessing was too strict
        valid_df = df.copy()
        valid_df['cleaned_text'] = valid_df['text'].astype(str).str.lower()

    X = valid_df['cleaned_text']
    y = valid_df['label']

    # 4. Train / Test Split
    test_size = 0.2 if len(valid_df) >= 20 else 0.25
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42,
            stratify=y
        )
    except Exception:
        # If stratification fails due to small class counts
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=42
        )

    # 5. TF-IDF Vectorization
    min_df = 2 if len(X_train) >= 30 else 1
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=min_df,
        max_df=0.95,
        max_features=5000,
        sublinear_tf=True
    )

    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # 6. Classification with Logistic Regression (optimized with multi-threaded BLAS)
    classifier = LogisticRegression(
        C=1.0,
        max_iter=1000,
        random_state=42,
        class_weight='balanced'
    )
    classifier.fit(X_train_tfidf, y_train)

    # 7. Model Evaluation
    y_pred = classifier.predict(X_test_tfidf)

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, pos_label='REAL', zero_division=0))
    rec = float(recall_score(y_test, y_pred, pos_label='REAL', zero_division=0))
    f1 = float(f1_score(y_test, y_pred, pos_label='REAL', zero_division=0))

    # Confusion matrix with explicit labels ['REAL', 'FAKE']
    cm = confusion_matrix(y_test, y_pred, labels=['REAL', 'FAKE'])
    cm_dict = {
        "matrix": cm.tolist(),
        "labels": ["REAL", "FAKE"],
        "actual_real_pred_real": int(cm[0][0]),
        "actual_real_pred_fake": int(cm[0][1]),
        "actual_fake_pred_real": int(cm[1][0]),
        "actual_fake_pred_fake": int(cm[1][1])
    }

    # 8. Save artifacts using joblib
    joblib.dump(classifier, CLASSIFIER_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    # 9. Save metadata
    metadata = {
        "is_trained": True,
        "algorithm": "Logistic Regression",
        "vectorizer": "TF-IDF (ngram_range=(1,2), max_features=5000)",
        "training_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_size_mb": file_size_mb,
        "total_samples": total_samples,
        "training_samples": len(X_train),
        "testing_samples": len(X_test),
        "dataset_sampling_note": dataset_sampling_note,
        "dataset_distribution": {
            "REAL": real_count,
            "FAKE": fake_count
        },
        "performance": {
            "accuracy": round(acc * 100, 2),
            "accuracy_ratio": round(acc, 4),
            "precision": round(prec * 100, 2),
            "precision_ratio": round(prec, 4),
            "recall": round(rec * 100, 2),
            "recall_ratio": round(rec, 4),
            "f1_score": round(f1 * 100, 2),
            "f1_score_ratio": round(f1, 4)
        },
        "confusion_matrix": cm_dict,
        "classes": list(classifier.classes_)
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata

def get_current_model_status() -> dict:
    """
    Checks if a trained model exists and returns status & metadata.
    """
    if os.path.exists(CLASSIFIER_PATH) and os.path.exists(VECTORIZER_PATH) and os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["is_trained"] = True
            return data
        except Exception:
            return {"is_trained": False, "message": "Model files are present but metadata could not be read."}
    return {
        "is_trained": False,
        "message": "No trained model found. Please train the model using a labelled dataset before analyzing news."
    }

def reset_model():
    """Removes saved model files (for testing/reset)."""
    for p in [CLASSIFIER_PATH, VECTORIZER_PATH, METADATA_PATH]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
