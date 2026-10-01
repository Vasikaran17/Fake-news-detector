import os
import sys
import pandas as pd
import requests

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATA_DIR = os.path.join(BASE_DIR, "sample_dataset")
os.makedirs(DATA_DIR, exist_ok=True)

TRUE_URL = "https://huggingface.co/datasets/Phoenyx83/ISOT-Fake-News-Dataset-FineTuned-2022/resolve/main/raw/True%20ok%20v2.csv"
FAKE_URL = "https://huggingface.co/datasets/Phoenyx83/ISOT-Fake-News-Dataset-FineTuned-2022/resolve/main/raw/Fake%20ok.csv"

def download_file(url, target_path, label):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 1000000:
        print(f"[{label}] File already exists at {target_path} ({os.path.getsize(target_path) / (1024*1024):.1f} MB). Skipping download.")
        return target_path

    print(f"[{label}] Downloading from {url}...")
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()
    total_size = int(r.headers.get('content-length', 0))
    downloaded = 0

    with open(target_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"\r[{label}] Progress: {downloaded/(1024*1024):.1f} / {total_size/(1024*1024):.1f} MB ({pct:.1f}%)", end="", flush=True)

    print(f"\n[{label}] Download complete!")
    return target_path

def prepare_and_train():
    true_raw_path = os.path.join(DATA_DIR, "raw_true.csv")
    fake_raw_path = os.path.join(DATA_DIR, "raw_fake.csv")
    combined_csv_path = os.path.join(DATA_DIR, "clement_bisaillon_dataset.csv")

    download_file(TRUE_URL, true_raw_path, "Real News (Reuters)")
    download_file(FAKE_URL, fake_raw_path, "Fake News")

    print("\nReading raw CSV files into Pandas...")
    try:
        df_true = pd.read_csv(true_raw_path, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df_true = pd.read_csv(true_raw_path, encoding='latin-1', low_memory=False)

    try:
        df_fake = pd.read_csv(fake_raw_path, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df_fake = pd.read_csv(fake_raw_path, encoding='latin-1', low_memory=False)

    print(f"Raw True rows: {len(df_true)}, Raw Fake rows: {len(df_fake)}")

    # Standardize to text and label columns
    df_true['label'] = 'REAL'
    df_fake['label'] = 'FAKE'

    # Ensure 'text' column exists
    for df in [df_true, df_fake]:
        if 'text' not in df.columns:
            for col in df.columns:
                if col.lower() in ['article', 'content', 'news']:
                    df.rename(columns={col: 'text'}, inplace=True)
                    break

    combined = pd.concat([
        df_true[['text', 'label']],
        df_fake[['text', 'label']]
    ], ignore_index=True)

    # Drop nulls and empty texts
    combined.dropna(subset=['text', 'label'], inplace=True)
    combined = combined[combined['text'].astype(str).str.strip() != '']

    # Shuffle
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"Combined clean dataset: {len(combined)} total articles.")
    print("Label distribution:\n", combined['label'].value_counts())

    print(f"Saving combined dataset to {combined_csv_path}...")
    combined.to_csv(combined_csv_path, index=False, encoding='utf-8')
    print("Saved successfully.")

    # Now train the model using our training pipeline
    from backend.services.training import train_fake_news_model
    print("\n--- Training Model with Clement Bisaillon Dataset ---")
    metadata = train_fake_news_model(combined_csv_path)

    print("\n=======================================================")
    print(" MODEL TRAINING SUCCESSFUL!")
    print(f" Accuracy : {metadata['performance']['accuracy']}%")
    print(f" Precision: {metadata['performance']['precision']}%")
    print(f" Recall   : {metadata['performance']['recall']}%")
    print(f" F1 Score : {metadata['performance']['f1_score']}%")
    print(f" Training Samples: {metadata['training_samples']}")
    print(f" Testing Samples : {metadata['testing_samples']}")
    print(" Confusion Matrix:", metadata['confusion_matrix'])
    print("=======================================================")

if __name__ == "__main__":
    prepare_and_train()
