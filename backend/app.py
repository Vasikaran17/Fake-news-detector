import os
import sys
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import FRONTEND_DIR, UPLOADS_DIR, MODELS_DIR
from backend.database import (
    init_db,
    get_system_stats,
    get_verification_history,
    get_evidence_for_verification,
    get_active_model_version
)
from backend.services.training import (
    train_fake_news_model,
    get_current_model_status,
    preview_csv,
    reset_model
)
from backend.services.news_fetcher import get_live_news, update_all_live_news
from backend.services.evidence_checker import verify_news_claim
from backend.services.continuous_learning import (
    get_continuous_learning_status,
    trigger_model_retraining_if_ready
)

# Initialize database tables
init_db()

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Maximum file upload size: 1.5 GB
app.config['MAX_CONTENT_LENGTH'] = 1500 * 1024 * 1024

# -------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------

@app.route("/")
def home_page():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/verify")
def verify_page():
    return send_from_directory(FRONTEND_DIR, "verify.html")

@app.route("/live")
def live_page():
    return send_from_directory(FRONTEND_DIR, "live.html")

@app.route("/history")
def history_page():
    return send_from_directory(FRONTEND_DIR, "history.html")

@app.route("/about")
def about_page():
    return send_from_directory(FRONTEND_DIR, "about.html")

# Keep train page accessible for developer/admin use
@app.route("/train")
def train_page():
    return send_from_directory(FRONTEND_DIR, "train.html")

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "css"), filename)

@app.route("/js/<path:filename>")
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "js"), filename)

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify backend status."""
    return jsonify({
        "status": "ok",
        "message": "Fake News Detector Live API is operational",
        "server_time": datetime.now().isoformat()
    }), 200

@app.route("/api/system-status", methods=["GET"])
def system_status_endpoint():
    """Returns live system statistics (connected status, articles checked, verified records, model version)."""
    stats = get_system_stats()
    return jsonify(stats), 200

@app.route("/api/model-status", methods=["GET"])
def model_status_endpoint():
    """Returns current model status, metadata, and versioning info."""
    status = get_current_model_status()
    active_version = get_active_model_version()
    if active_version:
        status["version_details"] = active_version
    return jsonify(status), 200

@app.route("/api/live-news", methods=["GET"])
def live_news_endpoint():
    """Returns currently retrieved news from configured live sources."""
    limit = request.args.get('limit', default=30, type=int)
    articles = get_live_news(limit=limit)
    return jsonify({
        "success": True,
        "count": len(articles),
        "articles": articles
    }), 200

@app.route("/api/update-news", methods=["POST"])
def update_news_endpoint():
    """Triggers an on-demand collection run across all configured live feeds and sources."""
    try:
        summary = update_all_live_news()
        # Check if continuous learning threshold has been reached
        retrain_result = trigger_model_retraining_if_ready()
        summary["retrain_result"] = retrain_result
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update live news: {str(e)}"}), 500

@app.route("/api/verify", methods=["POST"])
@app.route("/api/predict", methods=["POST"])  # Alias for backward compatibility
def verify_endpoint():
    """
    Evidence-based claim verification:
    Extracts claims, searches live evidence, computes ML prior,
    determines REAL / FAKE / UNCERTAIN, and records verification result.
    """
    data = request.get_json(silent=True) or request.form

    if not data or 'text' not in data:
        return jsonify({"error": "Please enter news content before verifying."}), 400

    news_text = data.get('text', '')
    if not news_text or not news_text.strip():
        return jsonify({"error": "Please enter news content before verifying."}), 400

    try:
        result = verify_news_claim(news_text)
        # Check if continuous learning threshold has been reached
        trigger_model_retraining_if_ready()
        return jsonify({
            "success": True,
            **result
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({
            "error": "Something went wrong while verifying this news article. Please try again."
        }), 500

@app.route("/api/verify-file", methods=["POST"])
@app.route("/api/predict-file", methods=["POST"])  # Alias for backward compatibility
def verify_file_endpoint():
    """
    Receives an uploaded news text file (.txt), extracts content,
    and runs evidence-based verification.
    """
    if 'file' not in request.files:
        return jsonify({"error": "Please upload a news text file."}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    allowed_extensions = ['.txt', '.text']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"error": "Please upload a supported text file (.txt)."}), 400

    try:
        content_bytes = file.read()
        try:
            news_text = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            news_text = content_bytes.decode('latin-1')

        if not news_text.strip():
            return jsonify({"error": "The uploaded text file is empty. Please provide a file with news content."}), 400

        result = verify_news_claim(news_text)
        trigger_model_retraining_if_ready()
        return jsonify({
            "success": True,
            "filename": file.filename,
            **result
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({
            "error": "Something went wrong while verifying the file. Please try again."
        }), 500

@app.route("/api/history", methods=["GET"])
def history_endpoint():
    """Returns stored user verification records with optional filtering (REAL, FAKE, UNCERTAIN)."""
    filter_res = request.args.get("filter", default=None)
    limit = request.args.get("limit", default=50, type=int)
    history = get_verification_history(limit=limit, filter_result=filter_res)
    return jsonify({
        "success": True,
        "count": len(history),
        "history": history
    }), 200

@app.route("/api/evidence/<int:verification_id>", methods=["GET"])
def evidence_endpoint(verification_id):
    """Returns evidence articles tied to a specific verification result."""
    items = get_evidence_for_verification(verification_id)
    return jsonify({
        "success": True,
        "verification_id": verification_id,
        "evidence": items
    }), 200

@app.route("/api/learning-status", methods=["GET"])
def learning_status_endpoint():
    """Returns continuous learning progress, verified records count, and retrain threshold."""
    status = get_continuous_learning_status()
    return jsonify(status), 200

# -------------------------------------------------------------
# Developer / Admin Endpoints (Maintained)
# -------------------------------------------------------------

@app.route("/api/preview-dataset", methods=["POST"])
def preview_dataset_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "Please upload a CSV file."}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected."}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Unsupported file format. Please upload a .csv file."}), 400

    filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOADS_DIR, f"preview_{filename}")
    file.save(temp_path)
    try:
        preview_data = preview_csv(temp_path)
        preview_data["filename"] = file.filename
        return jsonify({"success": True, "data": preview_data}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

@app.route("/api/train", methods=["POST"])
def train_endpoint():
    if 'file' not in request.files and 'dataset' not in request.files:
        return jsonify({"error": "Please upload a CSV dataset."}), 400
    file = request.files.get('file') or request.files.get('dataset')
    if not file or file.filename == '':
        return jsonify({"error": "No file selected for upload."}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Unsupported file format. Dataset must be a .csv file."}), 400

    filename = secure_filename(file.filename)
    saved_path = os.path.join(UPLOADS_DIR, f"training_{filename}")
    file.save(saved_path)
    try:
        metadata = train_fake_news_model(saved_path)
        return jsonify({
            "success": True,
            "message": "Model trained successfully!",
            "metadata": metadata
        }), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    finally:
        if os.path.exists(saved_path):
            try:
                os.remove(saved_path)
            except Exception:
                pass

@app.route("/api/reset-model", methods=["POST"])
def reset_model_endpoint():
    reset_model()
    return jsonify({"success": True, "message": "Model reset successfully."}), 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API route not found"}), 404
    return send_from_directory(FRONTEND_DIR, "index.html"), 404

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File size exceeds the 1.5 GB upload limit."}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Something went wrong on the server. Please try again."}), 500

if __name__ == "__main__":
    print("=" * 60)
    print(" Fake News Detector — Live & Continuously Updated System")
    print(" Running on: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
