"""
Unified Server for Portfolio Website & Android CMS Backend
Handles Public Content API, Authenticated Android CMS API, Media Serving, and Admin Dashboard.
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend.database import get_db_connection, init_db
from backend.api_cms import cms_bp
from cms.sync_engine import DriveSyncEngine, MANIFEST_PATH

app = Flask(__name__, static_folder=BASE_DIR)
app.register_blueprint(cms_bp)

sync_engine = DriveSyncEngine()
SYNC_INTERVAL_SECONDS = int(os.getenv("SYNC_INTERVAL_HOURS", 3)) * 3600
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "dragxsy_cms_2026")

# Enable CORS for Android client & development
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# ----------------------------------------------------------------------
# Background Scheduled Reconciliation Job
# ----------------------------------------------------------------------
def periodic_reconciliation():
    while True:
        time.sleep(SYNC_INTERVAL_SECONDS)
        print(f"[CMS Scheduler] Running scheduled reconciliation at {datetime.now()}...")
        try:
            sync_engine.sync()
        except Exception as e:
            print(f"[CMS Scheduler] Reconciliation error: {e}")

scheduler_thread = threading.Thread(target=periodic_reconciliation, daemon=True)
scheduler_thread.start()

# ----------------------------------------------------------------------
# Public Website Content API (STRICTLY 'published' content only)
# ----------------------------------------------------------------------
@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():
    """
    Returns public portfolio data from SQLite database.
    Strictly filters out drafts and unpublished projects.
    """
    conn = get_db_connection()
    categories_raw = conn.execute("""
        SELECT c.*, COUNT(p.id) as projects_count
        FROM categories c
        JOIN projects p ON c.id = p.category_id
        WHERE p.status = 'published'
        GROUP BY c.id
        ORDER BY c.sort_order ASC, c.created_at ASC
    """).fetchall()

    projects_raw = conn.execute("""
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM projects p
        JOIN categories c ON p.category_id = c.id
        WHERE p.status = 'published'
        ORDER BY p.sort_order ASC, p.created_at DESC
    """).fetchall()

    categories = [dict(c) for c in categories_raw]
    projects = []
    
    for r in projects_raw:
        p_dict = dict(r)
        p_dict["category"] = p_dict["category_name"]
        p_dict["tags"] = json.loads(p_dict.get("tags_json") or "[]")
        
        # Assets for gallery
        assets = conn.execute("SELECT * FROM assets WHERE project_id = ? ORDER BY sort_order ASC", (p_dict["id"],)).fetchall()
        p_dict["assets"] = [dict(a) for a in assets]
        
        # Cover asset formatting
        p_dict["coverAsset"] = {
            "localPath": p_dict.get("cover_asset_url") or "assets/hero.png",
            "sourceUrl": p_dict.get("cover_asset_url") or "assets/hero.png"
        }
        projects.append(p_dict)

    conn.close()

    # Fallback to manifest if database hasn't been seeded yet
    if len(projects) == 0:
        manifest = sync_engine.load_manifest()
        return jsonify(manifest)

    return jsonify({
        "version": 2,
        "source": "SQLite CMS Database",
        "lastSyncedAt": datetime.now().isoformat(),
        "syncStatus": "synced",
        "stats": {
            "categoriesCount": len(categories),
            "projectsCount": len(projects)
        },
        "categories": categories,
        "projects": projects
    })

@app.route("/api/categories", methods=["GET"])
def get_categories_public():
    """Returns published categories."""
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY sort_order ASC").fetchall()
    conn.close()
    return jsonify([dict(c) for c in categories])

@app.route("/api/projects", methods=["GET"])
def get_projects_public():
    """Returns only published projects for public viewing."""
    conn = get_db_connection()
    projects = conn.execute("SELECT * FROM projects WHERE status = 'published' ORDER BY sort_order ASC").fetchall()
    conn.close()
    return jsonify([dict(p) for p in projects])

@app.route("/api/projects/<slug>", methods=["GET"])
def get_project_public(slug):
    """Returns single published project with gallery assets."""
    conn = get_db_connection()
    proj = conn.execute("SELECT * FROM projects WHERE (slug = ? OR id = ?) AND status = 'published'", (slug, slug)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "Project not found or not published"}), 404

    p_dict = dict(proj)
    p_dict["tags"] = json.loads(p_dict.get("tags_json") or "[]")
    assets = conn.execute("SELECT * FROM assets WHERE project_id = ? ORDER BY sort_order ASC", (p_dict["id"],)).fetchall()
    p_dict["assets"] = [dict(a) for a in assets]
    conn.close()
    return jsonify(p_dict)

# ----------------------------------------------------------------------
# Media Uploads Serving
# ----------------------------------------------------------------------
@app.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploads(filename):
    uploads_dir = os.path.join(BASE_DIR, "uploads")
    return send_from_directory(uploads_dir, filename)

# ----------------------------------------------------------------------
# Legacy Sync & Webhook routes
# ----------------------------------------------------------------------
@app.route("/api/sync", methods=["POST"])
def trigger_sync():
    try:
        success = sync_engine.sync()
        manifest = sync_engine.load_manifest()
        return jsonify({
            "success": success,
            "message": "Synchronization completed",
            "stats": manifest.get("stats"),
            "lastSyncedAt": manifest.get("lastSyncedAt")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/webhook", methods=["POST"])
def drive_webhook():
    channel_id = request.headers.get("X-Goog-Channel-ID")
    resource_state = request.headers.get("X-Goog-Resource-State")
    if resource_state in ["add", "update", "trash", "change", "sync"]:
        threading.Thread(target=sync_engine.sync, daemon=True).start()
    return jsonify({"status": "received"}), 200

# ----------------------------------------------------------------------
# Admin CMS & Mobile Web Companion
# ----------------------------------------------------------------------
@app.route("/cms", methods=["GET"])
def mobile_cms_app():
    """Serves the Mobile CMS companion."""
    return send_from_directory(BASE_DIR, "mobile_cms.html")

@app.route("/admin/cms", methods=["GET"])
def admin_cms():
    manifest = sync_engine.load_manifest()
    conn = get_db_connection()
    db_projects = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Google Drive & Android CMS | dragxsy</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen p-6 md:p-12">
      <div class="max-w-4xl mx-auto space-y-8">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-cyan-400 animate-pulse"></span>
              <h1 class="text-2xl font-bold font-mono tracking-tight text-white">Private Portfolio CMS</h1>
            </div>
            <p class="text-xs text-slate-400 font-mono mt-1">Dual Source: Android App + Google Drive Sync</p>
          </div>
          <div class="flex items-center gap-3">
            <a href="/cms" target="_blank" class="px-4 py-2 rounded-xl bg-cyan-500/20 border border-cyan-500/40 text-xs font-mono text-cyan-300 hover:bg-cyan-500/30">Mobile CMS App ↗</a>
            <a href="/" class="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono hover:bg-slate-800 text-slate-300">View Site ↗</a>
          </div>
        </div>

        <div class="p-6 rounded-3xl bg-slate-900 border border-slate-800 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-bold font-mono text-cyan-400 uppercase tracking-wider">Database Projects Status (SQLite)</h2>
            <button onclick="importDrive()" class="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-mono text-cyan-400 border border-slate-700">Seed/Sync from Drive</button>
          </div>
          <div class="space-y-2">
            {% for p in db_projects %}
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800/80 flex items-center justify-between text-xs font-mono">
              <div class="flex items-center gap-3">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold {% if p.status == 'published' %}bg-emerald-950 text-emerald-400 border border-emerald-800{% else %}bg-amber-950 text-amber-400 border border-amber-800{% endif %}">{{ p.status }}</span>
                <span class="text-white font-bold">{{ p.title }}</span>
              </div>
              <span class="text-slate-500">{{ p.created_at }}</span>
            </div>
            {% endfor %}
          </div>
        </div>
      </div>
      <script>
        async function importDrive() {
          const resp = await fetch('/api/cms/import-drive', {
            method: 'POST',
            headers: {'Authorization': 'Bearer dragxsy_cms_2026'}
          });
          const res = await resp.json();
          alert(res.message || 'Imported!');
          window.location.reload();
        }
      </script>
    </body>
    </html>
    """
    return render_template_string(html, manifest=manifest, db_projects=db_projects)

# ----------------------------------------------------------------------
# Frontend Static File Routes
# ----------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/<path:path>", methods=["GET"])
def static_files(path):
    if os.path.exists(os.path.join(BASE_DIR, path)):
        return send_from_directory(BASE_DIR, path)
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    print(f"==================================================")
    print(f"[SERVER] Private Android CMS & Portfolio running on http://localhost:{port}")
    print(f"[MOBILE CMS] Open Mobile App: http://localhost:{port}/cms")
    print(f"[ADMIN] Admin Dashboard: http://localhost:{port}/admin/cms")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
