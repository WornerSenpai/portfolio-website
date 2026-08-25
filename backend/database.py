"""
Database Layer for Private Portfolio CMS
Relational SQLite schema for Users, Categories, Projects, Assets, Activity Logs, and Blog Posts.
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG_DB_PATH = os.path.join(BASE_DIR, "backend", "portfolio_cms.db")

if os.getenv("VERCEL"):
    DB_PATH = "/tmp/portfolio_cms.db"
    if not os.path.exists(DB_PATH) and os.path.exists(ORIG_DB_PATH):
        try:
            import shutil
            shutil.copy(ORIG_DB_PATH, DB_PATH)
        except Exception:
            pass
else:
    DB_PATH = ORIG_DB_PATH


def get_db_connection():
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables and default admin accounts."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    # Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        cover_asset_url TEXT,
        drive_folder_id TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Projects Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        category_id TEXT NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        year TEXT DEFAULT '2026',
        cover_asset_url TEXT,
        status TEXT DEFAULT 'published' CHECK(status IN ('draft', 'published', 'unpublished')),
        featured INTEGER DEFAULT 0,
        showcase_3d INTEGER DEFAULT 1,
        show_in_all INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        drive_folder_id TEXT,
        drive_url TEXT,
        tags_json TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        published_at TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
    )
    """)

    # Assets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        filename TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        original_url TEXT NOT NULL,
        optimized_url TEXT NOT NULL,
        card_url TEXT NOT NULL,
        thumbnail_url TEXT NOT NULL,
        width INTEGER DEFAULT 0,
        height INTEGER DEFAULT 0,
        size_bytes INTEGER DEFAULT 0,
        hash_sha256 TEXT,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    )
    """)

    # Blog Posts / Dispatches Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        tag TEXT NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        date TEXT NOT NULL,
        read_time TEXT NOT NULL,
        summary TEXT NOT NULL,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'published' CHECK(status IN ('draft', 'published', 'unpublished')),
        sort_order INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        published_at TEXT
    )
    """)

    # Activity Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id TEXT PRIMARY KEY,
        action TEXT NOT NULL,
        item_name TEXT NOT NULL,
        details TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()

    p_hash = generate_password_hash("dragxsy2026")
    now = datetime.now().isoformat()

    # Create / Update Primary Admin Account (senpaiworner@gmail.com)
    cursor.execute("SELECT id FROM users WHERE email = 'senpaiworner@gmail.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
            ("user_senpai", "senpaiworner@gmail.com", p_hash, "Sakshi (WornerSenpai)", now)
        )
        print("[DB] Initialized admin user: senpaiworner@gmail.com")
    else:
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'senpaiworner@gmail.com'", (p_hash,))

    # Create / Update Admin Account (admin@dragxsy.com)
    cursor.execute("SELECT id FROM users WHERE email = 'admin@dragxsy.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
            ("user_admin", "admin@dragxsy.com", p_hash, "Sakshi", now)
        )
        print("[DB] Initialized admin user: admin@dragxsy.com")
    else:
        cursor.execute("UPDATE users SET password_hash = ? WHERE email = 'admin@dragxsy.com'", (p_hash,))

    conn.commit()
    conn.close()

def log_activity(action, item_name, details=""):
    """Log an activity entry."""
    conn = get_db_connection()
    try:
        log_id = "act_" + str(uuid.uuid4())[:8]
        conn.execute(
            "INSERT INTO activity_logs (id, action, item_name, details, timestamp) VALUES (?, ?, ?, ?, ?)",
            (log_id, action, item_name, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    finally:
        conn.close()

# Auto-initialize on import
init_db()
