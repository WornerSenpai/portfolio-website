"""
Secure Authenticated CMS API Blueprint for Android Client
Handles JWT auth, Categories, Projects, Media Uploads, Blog Posts/Dispatches, Draft/Publish lifecycle, Activity stream.
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
JWT_EXPIRATION_HOURS = 72

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
    log_activity("LOGIN", "Mobile CMS", f"User {user['name']} logged in")

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
    return jsonify({"user": g.user})

# ----------------------------------------------------------------------
# 2. Home Overview Endpoint
# ----------------------------------------------------------------------
@cms_bp.route("/overview", methods=["GET"])
@require_auth
def get_overview():
    conn = get_db_connection()
    categories_count = conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()["cnt"]
    projects_count = conn.execute("SELECT COUNT(*) as cnt FROM projects").fetchone()["cnt"]
    published_count = conn.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'published'").fetchone()["cnt"]
    drafts_count = conn.execute("SELECT COUNT(*) as cnt FROM projects WHERE status = 'draft'").fetchone()["cnt"]
    posts_count = conn.execute("SELECT COUNT(*) as cnt FROM posts").fetchone()["cnt"]
    
    recent_activity = conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10").fetchall()
    conn.close()

    return jsonify({
        "userGreeting": f"Good morning, {g.user['name']}",
        "stats": {
            "categories": categories_count,
            "projects": projects_count,
            "published": published_count,
            "drafts": drafts_count,
            "posts": posts_count
        },
        "recentActivity": [dict(r) for r in recent_activity]
    })

# ----------------------------------------------------------------------
# 3. Categories Management
# ----------------------------------------------------------------------
@cms_bp.route("/categories", methods=["GET"])
@require_auth
def get_categories():
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
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Category name is required"}), 400

    slug = data.get("slug") or slugify(name)
    cover_url = data.get("coverAssetUrl") or "assets/hero.png"
    cat_id = "cat_" + str(uuid.uuid4())[:8]

    conn = get_db_connection()
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

@cms_bp.route("/categories/<cat_id>", methods=["DELETE"])
@require_auth
def delete_category(cat_id):
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

# ----------------------------------------------------------------------
# 4. Projects Management
# ----------------------------------------------------------------------
@cms_bp.route("/projects", methods=["GET"])
@require_auth
def get_projects():
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
        assets = conn.execute("SELECT * FROM assets WHERE project_id = ? ORDER BY sort_order ASC", (p_dict["id"],)).fetchall()
        p_dict["assets"] = [dict(a) for a in assets]
        projects.append(p_dict)

    conn.close()
    return jsonify(projects)

@cms_bp.route("/projects", methods=["POST"])
@require_auth
def create_project():
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
    status = data.get("status", "draft")
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

    asset_ids = data.get("assetIds", [])
    for idx, aid in enumerate(asset_ids):
        conn.execute("UPDATE assets SET project_id = ?, sort_order = ? WHERE id = ?", (proj_id, idx + 1, aid))

    conn.commit()
    conn.close()

    log_activity("CREATE_PROJECT", title, f"Status: {status}, Category: {cat['name']}")
    return jsonify({"success": True, "id": proj_id, "slug": slug, "status": status}), 201

@cms_bp.route("/projects/<project_id>/publish", methods=["PUT"])
@require_auth
def publish_project(project_id):
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

# ----------------------------------------------------------------------
# 5. Blog Posts / Dispatches Management (NEW)
# ----------------------------------------------------------------------
@cms_bp.route("/posts", methods=["GET"])
@require_auth
def get_posts():
    """List all blog posts including drafts."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM posts ORDER BY sort_order ASC, created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@cms_bp.route("/posts", methods=["POST"])
@require_auth
def create_post():
    """Create a new blog post/dispatch."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    tag = data.get("tag", "DISPATCH").strip().upper()
    summary = data.get("summary", "").strip()
    content = data.get("content", "").strip()
    read_time = data.get("readTime", "4 min read").strip()
    date_str = data.get("date", datetime.now().strftime("%b %Y"))
    status = data.get("status", "published")

    if not title or not content:
        return jsonify({"error": "Title and content are required"}), 400

    slug = data.get("slug") or slugify(title)
    post_id = "post_" + str(uuid.uuid4())[:8]

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM posts WHERE slug = ?", (slug,)).fetchone()
    if existing:
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"

    max_order = conn.execute("SELECT MAX(sort_order) as m FROM posts").fetchone()["m"] or 0
    now = datetime.now().isoformat()
    pub_at = now if status == 'published' else None

    conn.execute("""
        INSERT INTO posts (id, tag, title, slug, date, read_time, summary, content, status, sort_order, created_at, updated_at, published_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (post_id, tag, title, slug, date_str, read_time, summary, content, status, max_order + 1, now, now, pub_at))
    conn.commit()
    conn.close()

    log_activity("CREATE_POST", title, f"Status: {status}, Tag: {tag}")
    return jsonify({"success": True, "id": post_id, "slug": slug, "status": status}), 201

@cms_bp.route("/posts/<post_id>", methods=["PUT"])
@require_auth
def update_post(post_id):
    """Update an existing blog post."""
    data = request.get_json(silent=True) or {}
    
    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    title = data.get("title", post["title"]).strip()
    tag = data.get("tag", post["tag"]).strip().upper()
    summary = data.get("summary", post["summary"]).strip()
    content = data.get("content", post["content"]).strip()
    read_time = data.get("readTime", post["read_time"]).strip()
    status = data.get("status", post["status"])
    now = datetime.now().isoformat()
    pub_at = post["published_at"]
    if status == 'published' and not pub_at:
        pub_at = now

    conn.execute("""
        UPDATE posts
        SET title = ?, tag = ?, summary = ?, content = ?, read_time = ?, status = ?, updated_at = ?, published_at = ?
        WHERE id = ?
    """, (title, tag, summary, content, read_time, status, now, pub_at, post_id))
    conn.commit()
    conn.close()

    log_activity("UPDATE_POST", title, f"Status: {status}")
    return jsonify({"success": True, "message": "Post updated successfully"})

@cms_bp.route("/posts/<post_id>/publish", methods=["PUT"])
@require_auth
def publish_post(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT title FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    now = datetime.now().isoformat()
    conn.execute("UPDATE posts SET status = 'published', updated_at = ?, published_at = ? WHERE id = ?", (now, now, post_id))
    conn.commit()
    conn.close()

    log_activity("PUBLISH_POST", post["title"], "Published to live website")
    return jsonify({"success": True, "message": "Post published to live website", "status": "published"})

@cms_bp.route("/posts/<post_id>/unpublish", methods=["PUT"])
@require_auth
def unpublish_post(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT title FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    now = datetime.now().isoformat()
    conn.execute("UPDATE posts SET status = 'unpublished', updated_at = ? WHERE id = ?", (now, post_id))
    conn.commit()
    conn.close()

    log_activity("UNPUBLISH_POST", post["title"], "Hidden from live website")
    return jsonify({"success": True, "message": "Post unpublished", "status": "unpublished"})

@cms_bp.route("/posts/<post_id>", methods=["DELETE"])
@require_auth
def delete_post(post_id):
    conn = get_db_connection()
    post = conn.execute("SELECT title FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return jsonify({"error": "Post not found"}), 404

    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    log_activity("DELETE_POST", post["title"], f"ID: {post_id}")
    return jsonify({"success": True, "message": "Post deleted"})

# ----------------------------------------------------------------------
# 6. Media Upload Endpoint
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# 6. Media Upload & Asset Listing Endpoints
# ----------------------------------------------------------------------
@cms_bp.route("/assets", methods=["GET"])
@require_auth
def get_assets():
    """List all uploaded assets for the mobile CMS gallery."""
    conn = get_db_connection()
    assets = conn.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
    conn.close()
    
    asset_list = []
    for a in assets:
        asset_list.append({
            "id": a["id"],
            "filename": a["filename"],
            "mimeType": a["mime_type"],
            "originalUrl": a["original_url"],
            "optimizedUrl": a["optimized_url"],
            "cardUrl": a["card_url"],
            "thumbnailUrl": a["thumbnail_url"],
            "width": a["width"],
            "height": a["height"],
            "sizeBytes": a["size_bytes"],
            "createdAt": a["created_at"]
        })
    return jsonify(asset_list)

@cms_bp.route("/assets/<asset_id>", methods=["DELETE"])
@require_auth
def delete_asset(asset_id):
    """Delete an uploaded asset from database."""
    conn = get_db_connection()
    asset = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    if not asset:
        conn.close()
        return jsonify({"error": "Asset not found"}), 404
        
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()
    
    log_activity("DELETE_ASSET", asset["filename"], f"ID: {asset_id}")
    return jsonify({"success": True, "message": "Asset deleted"})

@cms_bp.route("/upload", methods=["POST"])
@require_auth
def upload_file():
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
    return jsonify({"success": True, "asset": asset_info}), 201

# ----------------------------------------------------------------------
# 7. Activity Logs Endpoint
# ----------------------------------------------------------------------
@cms_bp.route("/activity", methods=["GET"])
@require_auth
def get_activity():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 50").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])
