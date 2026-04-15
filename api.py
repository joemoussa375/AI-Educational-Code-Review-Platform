"""
AI Code Mentor - Flask REST API
Wraps code_reviewer.py as a REST API for the custom frontend.
Includes endpoints for review history, TA annotations, and dashboard analytics.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import gc
import torch
import time

# Import core engine and database
from code_reviewer import UnifiedCodeReviewer
from database import init_db, register_student, get_student, save_review, \
    get_reviews_by_student, get_all_reviews, get_review_by_id, \
    save_annotation, get_annotations_for_review, \
    get_class_analytics, get_students_summary, calculate_grade
import os

# ==========================================
# Colab Drive Caching Setup
# ==========================================
if os.path.exists("/content/drive/MyDrive"):
    os.environ['HF_HOME'] = '/content/drive/MyDrive/huggingface_cache'
    print(f"📁 Google Drive Cache Enabled: {os.environ['HF_HOME']}")
elif os.path.exists("/content"):
    print("⚠️ Google Drive not mounted. Model will download to temporary Colab storage.")
    print("   Tip: Mount your drive using the folder icon on the left before running this cell to cache the 4GB download!")

# ==========================================
# Flask App Setup
# ==========================================
app = Flask(__name__)
CORS(app)  # Allow frontend from any origin

import threading

# Global engine reference (loaded once)
engine = None
engine_lock = threading.Lock()

def get_engine():
    """Load the AI engine (singleton pattern)."""
    global engine
    with engine_lock:
        if engine is None:
            print("🤖 Initializing AI Code Review Engine...")
            engine = UnifiedCodeReviewer()
            print("✅ Engine ready!")
    return engine


# ==========================================
# Core API Endpoints
# ==========================================

@app.route("/api/health", methods=["GET"])
def health():
    """Health check — returns model status."""
    return jsonify({
        "status": "online" if engine else "model_not_loaded",
        "model": "Qwen2.5-Coder-7B-Instruct (4-bit)",
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"
    })


@app.route("/api/review", methods=["POST"])
def review():
    """
    Main review endpoint.
    Expects JSON: { "code": "def foo():...", "student_id": "250001" }
    Returns JSON: { "review": "...", "time": 12.3, "review_id": 1, "grade": 85 }
    """
    data = request.get_json()

    if not data or "code" not in data:
        return jsonify({"error": "Missing 'code' field in request body"}), 400

    code = data["code"].strip()
    student_id = data.get("student_id", "anonymous")

    if not code:
        return jsonify({"error": "Code cannot be empty"}), 400

    # Limit input size to prevent context overflow
    lines = code.split("\n")
    if len(lines) > 150:
        return jsonify({
            "error": f"Code too long ({len(lines)} lines). Maximum is 150 lines to ensure quality output."
        }), 400

    try:
        reviewer = get_engine()
        start = time.time()
        result = reviewer.review(code)
        elapsed = round(time.time() - start, 2)

        # Extract severity for grading
        severity = UnifiedCodeReviewer.extract_severity(result)
        critical_count = severity["critical_count"]
        style_count = severity["style_count"]
        grade = calculate_grade(critical_count, style_count)

        # Save to database
        saved = save_review(
            student_id=student_id,
            code_snippet=code,
            review_result=result,
            review_time_sec=elapsed,
            line_count=len(lines),
            critical_count=critical_count,
            style_count=style_count
        )

        # Cleanup GPU memory after review
        gc.collect()
        torch.cuda.empty_cache()

        return jsonify({
            "review": result,
            "time": elapsed,
            "lines": len(lines),
            "review_id": saved["id"],
            "grade": saved["grade"],
            "critical_count": critical_count,
            "style_count": style_count
        })

    except torch.cuda.OutOfMemoryError:
        gc.collect()
        torch.cuda.empty_cache()
        return jsonify({
            "error": "GPU out of memory. Try shorter code or restart the runtime."
        }), 503

    except Exception as e:
        return jsonify({"error": f"Review failed: {str(e)}"}), 500


@app.route("/api/load", methods=["POST"])
def load_model():
    """Trigger AI model loading in a background thread."""
    def background_task():
        try:
            get_engine()
        except Exception as e:
            print(f"Background load error: {e}")
            
    thread = threading.Thread(target=background_task)
    thread.start()
    return jsonify({"status": "loading_started"})


# ==========================================
# Student Endpoints
# ==========================================

@app.route("/api/student/register", methods=["POST"])
def register():
    """Register a student with their ID and name."""
    data = request.get_json()
    if not data or "student_id" not in data or "name" not in data:
        return jsonify({"error": "Missing 'student_id' or 'name'"}), 400
    
    student_id = data["student_id"].strip()
    name = data["name"].strip()
    
    if not student_id or not name:
        return jsonify({"error": "Student ID and name cannot be empty"}), 400
    
    result = register_student(student_id, name)
    return jsonify(result)


@app.route("/api/reviews/<student_id>", methods=["GET"])
def student_reviews(student_id):
    """Get all reviews for a specific student."""
    reviews = get_reviews_by_student(student_id)
    return jsonify({"reviews": reviews, "count": len(reviews)})


# ==========================================
# Staff Dashboard Endpoints
# ==========================================

@app.route("/api/reviews", methods=["GET"])
def all_reviews():
    """Get all reviews (staff dashboard). Supports pagination."""
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    reviews = get_all_reviews(limit, offset)
    return jsonify({"reviews": reviews, "count": len(reviews)})


@app.route("/api/review/<int:review_id>", methods=["GET"])
def single_review(review_id):
    """Get a single review by ID."""
    review = get_review_by_id(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404
    
    # Include annotations
    annotations = get_annotations_for_review(review_id)
    review["annotations"] = annotations
    return jsonify(review)


@app.route("/api/review/<int:review_id>/annotate", methods=["POST"])
def annotate_review(review_id):
    """Add a TA/Doctor annotation to a review."""
    data = request.get_json()
    if not data or "comment" not in data:
        return jsonify({"error": "Missing 'comment' field"}), 400
    
    staff_id = data.get("staff_id", "staff")
    comment = data["comment"].strip()
    
    if not comment:
        return jsonify({"error": "Comment cannot be empty"}), 400
    
    # Verify review exists
    review = get_review_by_id(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404
    
    result = save_annotation(review_id, staff_id, comment)
    return jsonify(result), 201


@app.route("/api/review/<int:review_id>/annotations", methods=["GET"])
def review_annotations(review_id):
    """Get all annotations for a review."""
    annotations = get_annotations_for_review(review_id)
    return jsonify({"annotations": annotations, "count": len(annotations)})


@app.route("/api/dashboard/analytics", methods=["GET"])
def dashboard_analytics():
    """Get class-wide analytics for the staff dashboard."""
    analytics = get_class_analytics()
    return jsonify(analytics)


@app.route("/api/dashboard/students", methods=["GET"])
def dashboard_students():
    """Get student summary list for the staff dashboard."""
    students = get_students_summary()
    return jsonify({"students": students, "count": len(students)})


# ==========================================
# Launch
# ==========================================
if __name__ == "__main__":
    # Initialize database
    init_db()
    print("⏳ Pre-loading AI Model into GPU (this takes 2-3 minutes)...", flush=True)
    get_engine()
    print("🚀 Model loaded! Starting Flask API...", flush=True)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
