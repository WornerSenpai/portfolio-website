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
DB_PATH = os.path.join(BASE_DIR, "backend", "portfolio_cms.db")

def get_db_connection():
    """Get SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables and default admin account."""
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

    # Create Default Admin Account (Sakshi) if not exists
    cursor.execute("SELECT id FROM users WHERE email = 'admin@dragxsy.com'")
    if not cursor.fetchone():
        admin_id = "user_" + str(uuid.uuid4())[:8]
        p_hash = generate_password_hash("dragxsy2026")
        cursor.execute(
            "INSERT INTO users (id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (admin_id, "admin@dragxsy.com", p_hash, "Sakshi", datetime.now().isoformat())
        )
        conn.commit()
        print("[DB] Initialized default admin user: admin@dragxsy.com")

    # Seed Initial Creative Notes/Dispatches if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM posts")
    if cursor.fetchone()["cnt"] == 0:
        initial_posts = [
            {
                "id": "post_dispatch_01",
                "tag": "DISPATCH 01",
                "title": "Operating Between Deliberate Chaos and Dark Aesthetics",
                "slug": "deliberate-chaos-and-dark-aesthetics",
                "date": "Aug 2026",
                "read_time": "4 min read",
                "summary": "Why deliberate imperfection, halftone artifacts, and raw analog noise resonate stronger than sanitized minimalist vectors in modern visual culture.",
                "content": "In an era of hyper-optimized UI kits and sanitized vectors, visual friction has become the ultimate luxury. When every brand looks like a clean white SaaS landing page, raw textures, brutalist grids, and deliberate grain force the human eye to pause and feel.\n\nCreating visuals across music covers and graphic apparel has taught me that true artistic memory isn't engineered through sterile symmetry—it's forged in tension. By combining disciplined typography with chaotic grit, the artwork develops an unmistakable identity that algorithms cannot fabricate.",
                "status": "published",
                "sort_order": 1
            },
            {
                "id": "post_dispatch_02",
                "tag": "DISPATCH 02",
                "title": "The Art of Album Cover Design in the Streaming Era",
                "slug": "album-cover-design-streaming-era",
                "date": "Jul 2026",
                "read_time": "5 min read",
                "summary": "How a 3000x3000px digital square must communicate an entire sonic universe at both miniature scale and full print fidelity.",
                "content": "A music cover is the front door to a sonic dimension. In streaming feeds where thousands of releases compete for a single thumb swipe, an album artwork must deliver instant emotional intrigue at 40x40 pixels while rewarding deep inspection at full gallery scale.\n\nMy process focuses on capturing the sonic frequency of the artist—translating raw distortion, ambient reverb, or sharp electronic percussion into corresponding visual textures and typographic choices.",
                "status": "published",
                "sort_order": 2
            },
            {
                "id": "post_dispatch_03",
                "tag": "DISPATCH 03",
                "title": "From Digital Concept to Heavyweight Screenprint",
                "slug": "digital-concept-to-heavyweight-screenprint",
                "date": "Jun 2026",
                "read_time": "4 min read",
                "summary": "Translating digital artwork into physical apparel: ink density, halftone separation, and textile storytelling.",
                "content": "Apparel design is kinetic art—your canvas moves, folds, and ages with the wearer. Designing for heavyweight garments demands understanding ink absorption, color halftones, and how a graphic placement interacts with the human silhouette.",
                "status": "published",
                "sort_order": 3
            }
        ]
        now = datetime.now().isoformat()
        for p in initial_posts:
            cursor.execute("""
                INSERT INTO posts (id, tag, title, slug, date, read_time, summary, content, status, sort_order, created_at, updated_at, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["tag"], p["title"], p["slug"], p["date"], p["read_time"], p["summary"], p["content"], p["status"], p["sort_order"], now, now, now))
        conn.commit()
        print("[DB] Seeded initial blog dispatches.")

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
