"""
Unified Dragxsy Portfolio & Private Mobile CMS Server
Handles public portfolio API, dynamic blog posts, media delivery, and CMS endpoints.
"""

from flask import Flask, send_from_directory, jsonify, send_file, request
import os
import json
from datetime import datetime

# Initialize Database & CMS Blueprint
from backend.database import init_db, get_db_connection
from backend.api_cms import cms_bp

# Initialize DB on startup
init_db()

app = Flask(__name__, static_folder=".", static_url_path="")

# Register Private CMS API Blueprint
app.register_blueprint(cms_bp)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
MANIFEST_PATH = os.path.join(BASE_DIR, "cms", "manifest.json")

# ----------------------------------------------------------------------
# Public Website Routes
# ----------------------------------------------------------------------
@app.route("/")
def serve_index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/cms")
def serve_mobile_cms():
    """Serve the mobile companion app interface."""
    return send_from_directory(BASE_DIR, "mobile_cms.html")

@app.route("/admin/cms")
def serve_admin_cms():
    """Alias for CMS interface."""
    return send_from_directory(BASE_DIR, "mobile_cms.html")

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serve processed media files."""
    return send_from_directory(UPLOADS_DIR, filename)

# ----------------------------------------------------------------------
# Public Portfolio & Blog Content API (Strictly Published Content)
# ----------------------------------------------------------------------
@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():
    """
    Public content endpoint used by frontend app.js.
    Queries database and returns ONLY published categories, projects, and blog dispatches.
    """
    conn = get_db_connection()

    # 1. Fetch Categories
    cat_rows = conn.execute("""
        SELECT c.*, COUNT(p.id) as published_projects_count
        FROM categories c
        LEFT JOIN projects p ON c.id = p.category_id AND p.status = 'published'
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.created_at ASC
    """).fetchall()
    
    categories = []
    for c in cat_rows:
        categories.append({
            "id": c["id"],
            "name": c["name"],
            "slug": c["slug"],
            "coverAssetUrl": c["cover_asset_url"] or "assets/hero.png",
            "count": c["published_projects_count"]
        })

    # 2. Fetch Strictly Published Projects
    proj_rows = conn.execute("""
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM projects p
        JOIN categories c ON p.category_id = c.id
        WHERE p.status = 'published'
        ORDER BY p.sort_order ASC, p.created_at DESC
    """).fetchall()

    projects = []
    for p in proj_rows:
        p_dict = dict(p)
        tags = json.loads(p_dict.get("tags_json") or "[]")
        
        # Assets for this project
        assets = conn.execute("""
            SELECT * FROM assets 
            WHERE project_id = ? 
            ORDER BY sort_order ASC
        """, (p_dict["id"],)).fetchall()

        asset_list = []
        for a in assets:
            asset_list.append({
                "id": a["id"],
                "filename": a["filename"],
                "thumbnail": a["thumbnail_url"],
                "card": a["card_url"],
                "url": a["optimized_url"] or a["original_url"],
                "width": a["width"],
                "height": a["height"]
            })

        projects.append({
            "id": p_dict["id"],
            "title": p_dict["title"],
            "slug": p_dict["slug"],
            "category": p_dict["category_name"],
            "categorySlug": p_dict["category_slug"],
            "description": p_dict["description"] or "",
            "year": p_dict["year"] or "2026",
            "coverAssetUrl": p_dict["cover_asset_url"] or (asset_list[0]["card"] if asset_list else "assets/hero.png"),
            "tags": tags,
            "featured": bool(p_dict["featured"]),
            "driveUrl": p_dict["drive_url"] or "https://drive.google.com/drive/folders/1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7?usp=drive_link",
            "assets": asset_list
        })

    # 3. Fetch Strictly Published Blog Dispatches
    post_rows = conn.execute("""
        SELECT * FROM posts
        WHERE status = 'published'
        ORDER BY sort_order ASC, created_at DESC
    """).fetchall()

    posts = []
    for post in post_rows:
        posts.append({
            "id": post["id"],
            "tag": post["tag"],
            "title": post["title"],
            "slug": post["slug"],
            "date": post["date"],
            "readTime": post["read_time"],
            "summary": post["summary"],
            "content": post["content"]
        })

    conn.close()

    return jsonify({
        "status": "success",
        "syncedAt": datetime.now().isoformat(),
        "categories": categories,
        "projects": projects,
        "posts": posts
    })

@app.route("/api/posts", methods=["GET"])
def get_public_posts():
    """Public endpoint specifically for blog articles."""
    conn = get_db_connection()
    post_rows = conn.execute("SELECT * FROM posts WHERE status = 'published' ORDER BY sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(p) for p in post_rows])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[SERVER] Starting unified dragxsy Portfolio & CMS on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
