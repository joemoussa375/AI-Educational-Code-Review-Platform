"""
AI Code Mentor - Database Module
SQLite-based persistence for reviews, students, and TA annotations.
"""

import sqlite3
import os
import threading
from datetime import datetime


# ==========================================
# Database Path Configuration
# ==========================================
def _get_db_path():
    """Determine the best location for the database file."""
    # Prefer Google Drive if mounted (persists across Colab sessions)
    drive_path = "/content/drive/MyDrive/ai_code_mentor"
    if os.path.exists("/content/drive/MyDrive"):
        os.makedirs(drive_path, exist_ok=True)
        return os.path.join(drive_path, "reviews.db")
    # Fallback: current directory
    return "reviews.db"


DB_PATH = _get_db_path()
_local = threading.local()


def _get_conn():
    """Get a thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


# ==========================================
# Schema Initialization
# ==========================================
def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            code_snippet TEXT NOT NULL,
            review_result TEXT NOT NULL,
            review_time_sec REAL,
            line_count INTEGER,
            critical_count INTEGER DEFAULT 0,
            style_count INTEGER DEFAULT 0,
            grade INTEGER DEFAULT 100,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        );

        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            staff_id TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (review_id) REFERENCES reviews(id)
        );

        CREATE INDEX IF NOT EXISTS idx_reviews_student ON reviews(student_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at);
        CREATE INDEX IF NOT EXISTS idx_annotations_review ON annotations(review_id);
    """)
    conn.commit()
    print(f"✅ Database ready at: {DB_PATH}")


# ==========================================
# Grading System
# ==========================================
def calculate_grade(critical_count, style_count):
    """
    Auto-grade a code review submission.
    
    Formula:
        Base = 100
        -15 per critical issue (security, logic bugs)
        -5 per style issue (PEP 8 violations)
        Floor at 0, cap at 100
    """
    grade = 100 - (critical_count * 15) - (style_count * 5)
    return max(0, min(100, grade))


# ==========================================
# Student Operations
# ==========================================
def register_student(student_id, name):
    """Register a new student or update their name."""
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO students (student_id, name) VALUES (?, ?)",
        (student_id, name)
    )
    conn.commit()
    return {"student_id": student_id, "name": name}


def get_student(student_id):
    """Get a student by ID."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    return dict(row) if row else None


# ==========================================
# Review Operations
# ==========================================
def save_review(student_id, code_snippet, review_result, review_time_sec, line_count, critical_count, style_count):
    """Save a completed review to the database. Returns the review dict."""
    grade = calculate_grade(critical_count, style_count)
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO reviews 
           (student_id, code_snippet, review_result, review_time_sec, line_count, critical_count, style_count, grade) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (student_id, code_snippet, review_result, review_time_sec, line_count, critical_count, style_count, grade)
    )
    conn.commit()
    return {
        "id": cursor.lastrowid,
        "grade": grade,
        "critical_count": critical_count,
        "style_count": style_count
    }


def get_reviews_by_student(student_id):
    """Get all reviews for a specific student, most recent first."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT id, student_id, code_snippet, review_result, review_time_sec, 
                  line_count, critical_count, style_count, grade, created_at 
           FROM reviews WHERE student_id = ? ORDER BY created_at DESC""",
        (student_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_reviews(limit=50, offset=0):
    """Get all reviews (for staff dashboard), most recent first."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT r.id, r.student_id, s.name as student_name, r.code_snippet, r.review_result,
                  r.review_time_sec, r.line_count, r.critical_count, r.style_count, r.grade, r.created_at
           FROM reviews r
           LEFT JOIN students s ON r.student_id = s.student_id
           ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
        (limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def get_review_by_id(review_id):
    """Get a single review by ID."""
    conn = _get_conn()
    row = conn.execute(
        """SELECT r.id, r.student_id, s.name as student_name, r.code_snippet, r.review_result,
                  r.review_time_sec, r.line_count, r.critical_count, r.style_count, r.grade, r.created_at
           FROM reviews r
           LEFT JOIN students s ON r.student_id = s.student_id
           WHERE r.id = ?""",
        (review_id,)
    ).fetchone()
    return dict(row) if row else None


# ==========================================
# Annotation Operations
# ==========================================
def save_annotation(review_id, staff_id, comment):
    """Add a TA/Doctor annotation to a review."""
    conn = _get_conn()
    cursor = conn.execute(
        "INSERT INTO annotations (review_id, staff_id, comment) VALUES (?, ?, ?)",
        (review_id, staff_id, comment)
    )
    conn.commit()
    return {"id": cursor.lastrowid, "review_id": review_id, "staff_id": staff_id, "comment": comment}


def get_annotations_for_review(review_id):
    """Get all annotations for a specific review."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM annotations WHERE review_id = ? ORDER BY created_at ASC",
        (review_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# ==========================================
# Dashboard Analytics
# ==========================================
def get_class_analytics():
    """Get aggregated class-wide statistics for the staff dashboard."""
    conn = _get_conn()
    
    stats = {}
    
    # Total reviews
    row = conn.execute("SELECT COUNT(*) as total FROM reviews").fetchone()
    stats["total_reviews"] = row["total"]
    
    # Active students
    row = conn.execute("SELECT COUNT(DISTINCT student_id) as total FROM reviews").fetchone()
    stats["active_students"] = row["total"]
    
    # Average review time
    row = conn.execute("SELECT AVG(review_time_sec) as avg_time FROM reviews").fetchone()
    stats["avg_review_time"] = round(row["avg_time"], 1) if row["avg_time"] else 0
    
    # Total critical issues flagged
    row = conn.execute("SELECT SUM(critical_count) as total FROM reviews").fetchone()
    stats["total_critical_issues"] = row["total"] or 0
    
    # Average grade
    row = conn.execute("SELECT AVG(grade) as avg FROM reviews").fetchone()
    stats["avg_grade"] = round(row["avg"], 1) if row["avg"] else 0
    
    # Reviews per day (last 30 days)
    rows = conn.execute(
        """SELECT DATE(created_at) as day, COUNT(*) as count 
           FROM reviews 
           WHERE created_at >= datetime('now', '-30 days')
           GROUP BY DATE(created_at) ORDER BY day"""
    ).fetchall()
    stats["reviews_per_day"] = [{"date": r["day"], "count": r["count"]} for r in rows]
    
    # Severity distribution
    row = conn.execute(
        """SELECT 
               SUM(critical_count) as critical,
               SUM(style_count) as style,
               SUM(CASE WHEN critical_count = 0 AND style_count = 0 THEN 1 ELSE 0 END) as clean
           FROM reviews"""
    ).fetchone()
    stats["severity_distribution"] = {
        "critical": row["critical"] or 0,
        "style": row["style"] or 0,
        "clean": row["clean"] or 0
    }
    
    # Grade distribution
    rows = conn.execute(
        """SELECT 
               CASE 
                   WHEN grade >= 90 THEN 'A (90-100)'
                   WHEN grade >= 80 THEN 'B (80-89)'
                   WHEN grade >= 70 THEN 'C (70-79)'
                   WHEN grade >= 60 THEN 'D (60-69)'
                   ELSE 'F (0-59)'
               END as bracket,
               COUNT(*) as count
           FROM reviews GROUP BY bracket ORDER BY bracket"""
    ).fetchall()
    stats["grade_distribution"] = [{"bracket": r["bracket"], "count": r["count"]} for r in rows]
    
    return stats


def get_students_summary():
    """Get a summary of all students for the staff dashboard."""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT 
               s.student_id,
               s.name,
               COUNT(r.id) as total_reviews,
               COALESCE(SUM(r.critical_count), 0) as total_critical,
               COALESCE(SUM(r.style_count), 0) as total_style,
               ROUND(COALESCE(AVG(r.grade), 0), 1) as avg_grade,
               MAX(r.created_at) as last_active
           FROM students s
           LEFT JOIN reviews r ON s.student_id = r.student_id
           GROUP BY s.student_id, s.name
           ORDER BY last_active DESC"""
    ).fetchall()
    
    result = []
    for r in rows:
        d = dict(r)
        # Calculate risk level based on average grade
        avg = d["avg_grade"]
        if avg >= 80:
            d["risk_level"] = "low"
        elif avg >= 60:
            d["risk_level"] = "medium"
        else:
            d["risk_level"] = "high"
        result.append(d)
    
    return result
