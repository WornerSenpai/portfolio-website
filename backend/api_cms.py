"""
Secure Authenticated CMS API Blueprint for Android Client
Handles JWT auth, Categories, Projects, Media Uploads, Draft/Publish lifecycle, Reordering, Activity stream.
"""

import os
import json
import uuid
import re
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, g
from werkzeug.security import check_password_hash

from backend.database import get_db_connection, log_activity
from backend.storage import is_allowed_file, process_and_store_image, MAX_FILE_SIZE

cms_bp = Blueprint("cms_api", __name__, url_prefix="/api/cms")

JWT_SECRET = os.getenv("JWT_SECRET", "dragxsy_android_cms_jwt_secret_2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 72 # 3 days access token

# ----------------------------------------------------------------------
# Auth Helpers & Decorator
# ----------------------------------------------------------------------
def generate_token(user_id, email, name):
    payload = {
        "userId": user_id,
        "email": email,
        "name": name,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization token"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            g.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired, please login again"}), 401
        except Exception:
            return jsonify({"error": "Invalid token authentication"}), 401
        
        return f(*args, **kwargs)
    return decorated

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'^[0-9]+[_\-\s]+', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or "item"

# ----------------------------------------------------------------------
# 1. Authentication Endpoints
# ----------------------------------------------------------------------
@cms_bp.route("/auth/login", methods=["POST"])
def login():
    """Authenticate Android client and issue JWT token."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user["id"], user["email"], user["name"])
    log_activity("LOGIN", "Android App", f"User {user['name']} logged in")

    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
    })

@cms_bp.route("/auth/me", methods=["GET"])
@require_auth
def get_me():
    """Get current authenticated user info."""
    return jsonify({
        "user": g.user
    })

# ----------------------------------------------------------------------
# 2. Home Overview Endpoint
# ----------------------------------------------------------------------
@cms_bp.route("/overview", methods=["GET"])
@require_auth
def get_overview():
    """Home screen metrics and recent activity."""
    conn = get_db_connection()
    
    categories_count = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()["cnt"]
    projects_count = conn.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]
    published_count = conn.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'published'").fetchone()["cnt"]
    drafts_count = conn.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'draft'").fetchone()["cnt"]
    
    recent_activity = conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10").fetchall()
    conn.close()

    return jsonify({
        "userGreeting": f"Good morning, {g.user['name']}",
        "stats": {
            "categories": categories_count,
            "projects": projects_count,
            "published": published_count,
            "drafts": drafts_count
        },
        "recentActivity": [dict(r) for r in recent_activity]
    })

# ----------------------------------------------------------------------
# 3. Categories Management
# ----------------------------------------------------------------------
@cms_bp.route("/categories", methods=["GET"])
@require_auth
def get_categories():
    """List all categories with project counts."""
    conn = get_db_connection()
    categories = conn.execute("""
        SELECT c.*, COUNT(p.id) as projects_count 
        FROM categories c
        LEFT JOIN projects p ON c.id = p.category_id
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.created_at ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(c) for c in categories])

@cms_bp.route("/categories", methods=["POST"])
@require_auth
def create_category():
    """Create a new category from Android."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Category name is required"}), 400

    slug = data.get("slug") or slugify(name)
    cover_url = data.get("coverAssetUrl") or "assets/hero.png"
    cat_id = "cat_" + str(uuid.uuid4())[:8]

    conn = get_db_connection()
    # Check duplicate slug
    existing = conn.execute("SELECT id FROM categories WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"

    max_order = conn.execute("SELECT MAX(sort_order) as m FROM categories").fetchone()["m"] or 0
    now = datetime.now().isoformat()

    conn.execute(
        "INSERT INTO categories (id, name, slug, cover_asset_url, sort_order, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cat_id, name, slug, cover_url, max_order + 1, now, now)
    )
    conn.commit()
    conn.close()

    log_activity("CREATE_CATEGORY", name, f"ID: {cat_id}")
    return jsonify({"success": True, "id": cat_id, "name": name, "slug": slug}), 201

@cms_bp.route("/categories/<cat_id>", methods=["PUT"])
@require_auth
def update_category(cat_id):
    """Update an existing category."""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    cover_url = data.get("coverAssetUrl")

    conn = get_db_connection()
    cat = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if not cat:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    new_name = name or cat["name"]
    new_cover = cover_url if cover_url is not None else cat["cover_asset_url"]
    now = datetime.now().isoformat()

    conn.execute(
        "UPDATE categories SET name = ?, cover_asset_url = ?, updated_at = ? WHERE id = ?",
        (new_name, new_cover, now, cat_id)
    )
    conn.commit()
    conn.close()

    log_activity("UPDATE_CATEGORY", new_name, f"ID: {cat_id}")
    return jsonify({"success": True, "message": "Category updated"})

@cms_bp.route("/categories/<cat_id>", methods=["DELETE"])
@require_auth
def delete_category(cat_id):
    """Delete a category."""
    conn = get_db_connection()
    cat = conn.execute("SELECT name FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if not cat:
        conn.close()
        return jsonify({"error": "Category not found"}), 404

    conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()

    log_activity("DELETE_CATEGORY", cat["name"], f"ID: {cat_id}")
    return jsonify({"success": True, "message": "Category deleted"})

@cms_bp.route("/categories/reorder", methods=["PUT"])
@require_auth
def reorder_categories():
    """Reorder categories."""
    data = request.get_json(silent=True) or {}
    order_list = data.get("order", []) # Array of category IDs in order

    conn = get_db_connection()
    for index, cid in enumerate(order_list):
        conn.execute("UPDATE categories SET sort_order = ? WHERE id = ?", (index + 1, cid))
    conn.commit()
    conn.close()

    log_activity("REORDER_CATEGORIES", "Categories", f"Updated order for {len(order_list)} categories")
    return jsonify({"success": True, "message": "Categories reordered"})

# ----------------------------------------------------------------------
# 4. Projects Management
# ----------------------------------------------------------------------
@cms_bp.route("/projects", methods=["GET"])
@require_auth
def get_projects():
    """List all projects with category names and assets."""
    status_filter = request.args.get("status")
    category_id = request.args.get("categoryId")

    query = """
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM projects p
        JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if status_filter and status_filter != 'all':
        query += " AND p.status = ?"
        params.append(status_filter)
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)

    query += " ORDER BY p.sort_order ASC, p.created_at DESC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()

    projects = []
    for r in rows:
        p_dict = dict(r)
        p_dict["tags"] = json.loads(p_dict.get("tags_json") or "[]")
        # Fetch assets
        assets = conn.execute("SELECT * FROM assets WHERE project_id = ? ORDER BY sort_order ASC", (p_dict["id"],)).fetchall()
        p_dict["assets"] = [dict(a) for a in assets]
        projects.append(p_dict)

    conn.close()
    return jsonify(projects)

@cms_bp.route("/projects/<project_id>", methods=["GET"])
@require_auth
def get_project_detail(project_id):
    """Get project details including all gallery assets."""
    conn = get_db_connection()
    row = conn.execute("""
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM projects p
        JOIN categories c ON p.category_id = c.id
        WHERE p.id = ? OR p.slug = ?
    """, (project_id, project_id)).fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    p_dict = dict(row)
    p_dict["tags"] = json.loads(p_dict.get("tags_json") or "[]")
    assets = conn.execute("SELECT * FROM assets WHERE project_id = ? ORDER BY sort_order ASC", (p_dict["id"],)).fetchall()
    p_dict["assets"] = [dict(a) for a in assets]
    conn.close()

    return jsonify(p_dict)

@cms_bp.route("/projects", methods=["POST"])
@require_auth
def create_project():
    """Create a new project from Android CMS."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    category_id = data.get("categoryId")
    
    if not title or not category_id:
        return jsonify({"error": "Title and category are required"}), 400

    conn = get_db_connection()
    cat = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not cat:
        conn.close()
        return jsonify({"error": "Invalid category ID"}), 400

    slug = data.get("slug") or slugify(title)
    existing = conn.execute("SELECT id FROM projects WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"

    proj_id = "proj_" + str(uuid.uuid4())[:8]
    description = data.get("description", "")
    year = data.get("year", "2026")
    status = data.get("status", "draft") # 'draft' or 'published'
    featured = 1 if data.get("featured") else 0
    cover_url = data.get("coverAssetUrl") or "assets/hero.png"
    tags_json = json.dumps(data.get("tags", [cat["name"], "Artwork"]))
    drive_url = data.get("driveUrl", "https://drive.google.com/drive/folders/1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7?usp=drive_link")
    
    now = datetime.now().isoformat()
    pub_at = now if status == 'published' else None
    max_order = conn.execute("SELECT MAX(sort_order) as m FROM projects WHERE category_id = ?", (category_id,)).fetchone()["m"] or 0

    conn.execute("""
        INSERT INTO projects (id, category_id, title, slug, description, year, cover_asset_url, status, featured, sort_order, tags_json, drive_url, created_at, updated_at, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (proj_id, category_id, title, slug, description, year, cover_url, status, featured, max_order + 1, tags_json, drive_url, now, now, pub_at))

    # Link any asset IDs provided
    asset_ids = data.get("assetIds", [])
    for idx, aid in enumerate(asset_ids):
        conn.execute("UPDATE assets SET project_id = ?, sort_order = ? WHERE id = ?", (proj_id, idx + 1, aid))

    conn.commit()
    conn.close()

    log_activity("CREATE_PROJECT", title, f"Status: {status}, Category: {cat['name']}")
    return jsonify({"success": True, "id": proj_id, "slug": slug, "status": status}), 201

@cms_bp.route("/projects/<project_id>", methods=["PUT"])
@require_auth
def update_project(project_id):
    """Update project details from Android."""
    data = request.get_json(silent=True) or {}
    
    conn = get_db_connection()
    proj = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    title = data.get("title", proj["title"]).strip()
    category_id = data.get("categoryId", proj["category_id"])
    description = data.get("description", proj["description"])
    year = data.get("year", proj["year"])
    cover_url = data.get("coverAssetUrl", proj["cover_asset_url"])
    featured = 1 if data.get("featured", proj["featured"]) else 0
    tags = data.get("tags")
    tags_json = json.dumps(tags) if tags is not None else proj["tags_json"]
    status = data.get("status", proj["status"])
    now = datetime.now().isoformat()
    pub_at = proj["published_at"]
    if status == 'published' and not pub_at:
        pub_at = now

    conn.execute("""
        UPDATE projects 
        SET title = ?, category_id = ?, description = ?, year = ?, cover_asset_url = ?, status = ?, featured = ?, tags_json = ?, updated_at = ?, published_at = ?
        WHERE id = ?
    """, (title, category_id, description, year, cover_url, status, featured, tags_json, now, pub_at, project_id))

    # Update asset linkages if passed
    if "assetIds" in data:
        for idx, aid in enumerate(data["assetIds"]):
            conn.execute("UPDATE assets SET project_id = ?, sort_order = ? WHERE id = ?", (project_id, idx + 1, aid))

    conn.commit()
    conn.close()

    log_activity("UPDATE_PROJECT", title, f"Status: {status}")
    return jsonify({"success": True, "message": "Project updated"})

@cms_bp.route("/projects/<project_id>/publish", methods=["PUT"])
@require_auth
def publish_project(project_id):
    """Publish a project directly to the live website."""
    conn = get_db_connection()
    proj = conn.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    now = datetime.now().isoformat()
    conn.execute("UPDATE projects SET status = 'published', updated_at = ?, published_at = ? WHERE id = ?", (now, now, project_id))
    conn.commit()
    conn.close()

    log_activity("PUBLISH_PROJECT", proj["title"], "Published to live website")
    return jsonify({"success": True, "message": "Project published to live website", "status": "published"})

@cms_bp.route("/projects/<project_id>/unpublish", methods=["PUT"])
@require_auth
def unpublish_project(project_id):
    """Unpublish a project from the live website."""
    conn = get_db_connection()
    proj = conn.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    now = datetime.now().isoformat()
    conn.execute("UPDATE projects SET status = 'unpublished', updated_at = ? WHERE id = ?", (now, project_id))
    conn.commit()
    conn.close()

    log_activity("UNPUBLISH_PROJECT", proj["title"], "Hidden from live website")
    return jsonify({"success": True, "message": "Project unpublished", "status": "unpublished"})

@cms_bp.route("/projects/<project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id):
    """Delete a project."""
    conn = get_db_connection()
    proj = conn.execute("SELECT title FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "Project not found"}), 404

    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    log_activity("DELETE_PROJECT", proj["title"], f"ID: {project_id}")
    return jsonify({"success": True, "message": "Project deleted"})

@cms_bp.route("/projects/reorder", methods=["PUT"])
@require_auth
def reorder_projects():
    """Reorder projects."""
    data = request.get_json(silent=True) or {}
    order_list = data.get("order", [])

    conn = get_db_connection()
    for index, pid in enumerate(order_list):
        conn.execute("UPDATE projects SET sort_order = ? WHERE id = ?", (index + 1, pid))
    conn.commit()
    conn.close()

    log_activity("REORDER_PROJECTS", "Projects", f"Updated order for {len(order_list)} projects")
    return jsonify({"success": True, "message": "Projects reordered"})

# ----------------------------------------------------------------------
# 5. Media Upload Endpoint
# ----------------------------------------------------------------------
@cms_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
    """Handle multipart media upload from Android."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename or "artwork.jpg"
    mime_type = file.mimetype or "image/jpeg"

    if not is_allowed_file(filename, mime_type):
        return jsonify({"error": "Unsupported file format. Supported: JPG, PNG, WEBP, GIF, MP4, MOV"}), 400

    try:
        asset_info = process_and_store_image(file, filename)
    except Exception as e:
        return jsonify({"error": f"Failed to process media: {str(e)}"}), 500

    # Save to SQLite Database
    conn = get_db_connection()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO assets (id, filename, mime_type, original_url, optimized_url, card_url, thumbnail_url, width, height, size_bytes, hash_sha256, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        asset_info["id"],
        asset_info["filename"],
        mime_type,
        asset_info["originalUrl"],
        asset_info["optimizedUrl"],
        asset_info["cardUrl"],
        asset_info["thumbnailUrl"],
        asset_info["width"],
        asset_info["height"],
        asset_info["sizeBytes"],
        asset_info["hash"],
        now
    ))
    conn.commit()
    conn.close()

    log_activity("UPLOAD_MEDIA", filename, f"Size: {round(asset_info['sizeBytes']/1024, 1)} KB")
    return jsonify({
        "success": True,
        "asset": asset_info
    }), 201

# ----------------------------------------------------------------------
# 6. One-Time Google Drive Import
# ----------------------------------------------------------------------
@cms_bp.route("/import-drive", methods=["POST"])
@require_auth
def import_drive():
    """One-time migration from existing Google Drive manifest into SQLite database."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(base_dir, "cms", "manifest.json")

    if not os.path.exists(manifest_path):
        return jsonify({"error": "Drive manifest not found to import"}), 404

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    conn = get_db_connection()
    imported_cats = 0
    imported_projs = 0

    now = datetime.now().isoformat()

    # Import categories
    for cat in manifest.get("categories", []):
        cat_id = cat.get("id") or f"cat_{cat['slug']}"
        existing = conn.execute("SELECT id FROM categories WHERE id = ? OR slug = ?", (cat_id, cat["slug"])).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO categories (id, name, slug, cover_asset_url, drive_folder_id, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat_id, cat["name"], cat["slug"], "assets/hero.png", cat.get("driveFolderId"), cat.get("order", 1), now, now))
            imported_cats += 1

    # Import projects
    for proj in manifest.get("projects", []):
        proj_id = proj.get("id") or f"proj_{proj['slug']}"
        existing = conn.execute("SELECT id FROM projects WHERE id = ? OR slug = ?", (proj_id, proj["slug"])).fetchone()
        if not existing:
            cat_id = proj.get("categoryId") or f"cat_{slugify(proj['category'])}"
            cover_url = proj.get("coverAsset", {}).get("localPath") or "assets/hero.png"
            tags_json = json.dumps(proj.get("tags", [proj.get("category", "Artwork")]))
            drive_url = proj.get("driveUrl", "https://drive.google.com/drive/folders/1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7?usp=drive_link")
            
            conn.execute("""
                INSERT INTO projects (id, category_id, title, slug, description, year, cover_asset_url, status, featured, sort_order, tags_json, drive_url, created_at, updated_at, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (proj_id, cat_id, proj["title"], proj["slug"], proj.get("description", ""), proj.get("year", "2026"), cover_url, 'published', 0, proj.get("order", 1), tags_json, drive_url, now, now, now))
            imported_projs += 1

    conn.commit()
    conn.close()

    log_activity("IMPORT_DRIVE", "Google Drive Portfolio", f"Migrated {imported_cats} categories, {imported_projs} projects into CMS DB")
    return jsonify({
        "success": True,
        "message": f"Successfully migrated {imported_cats} categories and {imported_projs} projects into database",
        "categoriesImported": imported_cats,
        "projectsImported": imported_projs
    })

# ----------------------------------------------------------------------
# 7. Activity Logs Endpoint
# ----------------------------------------------------------------------
@cms_bp.route("/activity", methods=["GET"])
@require_auth
def get_activity():
    """Get activity logs."""
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])
