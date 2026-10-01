import os
import shutil
import json
import pandas as pd
from datetime import datetime
from backend.config import (
    MODEL_UPDATE_THRESHOLD,
    VERIFIED_CSV_PATH,
    CURRENT_MODEL_DIR,
    ARCHIVE_MODEL_DIR,
    BASE_DIR
)
from backend.database import (
    get_verified_data_count,
    get_all_verified_training_records,
    get_active_model_version,
    record_model_version
)
from backend.services.training import train_fake_news_model

BASELINE_DATASET_PATH = os.path.join(BASE_DIR, "sample_dataset", "clement_bisaillon_dataset.csv")

def sync_verified_data_to_csv():
    """
    Exports all verified records from SQLite into data/verified_news.csv.
    Maintains clean backup for continuous learning.
    """
    records = get_all_verified_training_records()
    if not records:
        # Create empty CSV with required headers if no records yet
        df = pd.DataFrame(columns=["text", "label", "source", "source_url", "verified_at"])
        df.to_csv(VERIFIED_CSV_PATH, index=False, encoding="utf-8")
        return 0

    df = pd.DataFrame(records)
    df.to_csv(VERIFIED_CSV_PATH, index=False, encoding="utf-8")
    return len(df)

def get_continuous_learning_status() -> dict:
    """
    Returns current continuous learning status:
    - total verified records
    - threshold for next automatic retrain
    - active model version
    - progress percentage toward next version
    """
    total_verified = get_verified_data_count()
    active_model = get_active_model_version()
    current_ver = active_model["version"] if active_model else "v1.0"

    # Calculate records since last training
    trained_records = active_model["training_records"] if active_model else 0
    records_since = total_verified % MODEL_UPDATE_THRESHOLD

    progress_pct = round((records_since / MODEL_UPDATE_THRESHOLD) * 100, 1)

    records_until = max(0, MODEL_UPDATE_THRESHOLD - records_since)

    return {
        "active_model_version": current_ver,
        "current_model_version": current_ver,
        "total_verified_records": total_verified,
        "update_threshold": MODEL_UPDATE_THRESHOLD,
        "model_update_threshold": MODEL_UPDATE_THRESHOLD,
        "records_toward_threshold": records_since,
        "records_until_retrain": records_until,
        "retrain_progress_percentage": min(progress_pct, 100.0),
        "is_retrain_ready": records_since >= MODEL_UPDATE_THRESHOLD or total_verified >= MODEL_UPDATE_THRESHOLD,
        "verified_csv_path": VERIFIED_CSV_PATH
    }

def trigger_model_retraining_if_ready() -> dict:
    """
    Checks if verified record threshold is reached. If so, automatically
    retrains the model, evaluates it, versions the artifacts, and promotes it
    if it satisfies quality benchmarks.
    """
    status = get_continuous_learning_status()
    total_verified = status["total_verified_records"]

    if total_verified < MODEL_UPDATE_THRESHOLD:
        return {
            "retrained": False,
            "message": f"Threshold not reached ({status['records_toward_threshold']}/{MODEL_UPDATE_THRESHOLD} verified records)."
        }

    print(f"[ContinuousLearning] Threshold reached ({total_verified} records). Initiating model update...")

    # 1. Sync verified records to CSV
    sync_verified_data_to_csv()

    # 2. Combine baseline dataset with verified new records
    verified_records = get_all_verified_training_records()
    df_verified = pd.DataFrame(verified_records)[["text", "label"]]

    if os.path.exists(BASELINE_DATASET_PATH):
        try:
            df_baseline = pd.read_csv(BASELINE_DATASET_PATH, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            df_baseline = pd.read_csv(BASELINE_DATASET_PATH, encoding="latin-1", low_memory=False)
        df_combined = pd.concat([df_baseline[["text", "label"]], df_verified], ignore_index=True)
    else:
        df_combined = df_verified

    df_combined.dropna(subset=["text", "label"], inplace=True)
    df_combined = df_combined.sample(frac=1, random_state=42).reset_index(drop=True)

    temp_train_path = os.path.join(BASE_DIR, "data", "retrain_dataset.csv")
    df_combined.to_csv(temp_train_path, index=False, encoding="utf-8")

    # 3. Train new candidate model
    try:
        new_meta = train_fake_news_model(temp_train_path)
    finally:
        if os.path.exists(temp_train_path):
            try:
                os.remove(temp_train_path)
            except Exception:
                pass

    new_acc = new_meta["performance"]["accuracy"]

    # 4. Model Evaluation & Version Promotion Guard
    # Only promote if accuracy is >= 90%
    if new_acc < 90.0:
        return {
            "retrained": False,
            "message": f"Candidate model failed accuracy criteria ({new_acc}% < 90.0%). Active model retained."
        }

    # Generate new version number (e.g. v1.1, v1.2)
    active_model = get_active_model_version()
    current_ver = active_model["version"] if active_model else "v1.0"

    try:
        v_num = float(current_ver.replace("v", ""))
        new_version = f"v{round(v_num + 0.1, 1)}"
    except Exception:
        new_version = f"{current_ver}_next"

    # Save to archive
    archive_dir = os.path.join(ARCHIVE_MODEL_DIR, f"model_{new_version}")
    os.makedirs(archive_dir, exist_ok=True)

    legacy_model_dir = os.path.join(os.path.dirname(__file__), "..", "model")
    for f in ["classifier.pkl", "vectorizer.pkl", "model_metadata.json"]:
        src_f = os.path.join(legacy_model_dir, f)
        if os.path.exists(src_f):
            shutil.copy(src_f, os.path.join(archive_dir, f))
            shutil.copy(src_f, os.path.join(CURRENT_MODEL_DIR, f))

    # Record in database
    perf = new_meta["performance"]
    record_model_version(
        version=new_version,
        training_records=new_meta["training_samples"],
        accuracy=perf["accuracy"],
        precision=perf["precision"],
        recall=perf["recall"],
        f1_score=perf["f1_score"]
    )

    print(f"[ContinuousLearning] Successfully promoted new model version: {new_version} (Accuracy: {new_acc}%)")

    return {
        "retrained": True,
        "new_version": new_version,
        "accuracy": new_acc,
        "training_samples": new_meta["training_samples"],
        "message": f"Continuous learning pipeline successfully deployed new model version {new_version}."
    }
