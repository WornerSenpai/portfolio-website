"""
Secure Server-Side GitHub Assets Pipeline for dragxsy Portfolio & CMS
Validates image files, sanitizes filenames, and commits assets directly
to GitHub repository under `assets/<category_slug>/<filename>`.
"""

import os
import io
import re
import uuid
import json
import base64
import hashlib
import urllib.request
from PIL import Image

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "WornerSenpai")
GITHUB_REPO = os.getenv("GITHUB_REPO", "portfolio-website")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

ASSETS_ROOT = os.path.join(BASE_DIR, "assets")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'mp4', 'mov', 'webm'}
ALLOWED_MIMES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/svg+xml',
    'video/mp4', 'video/quicktime', 'video/webm'
}
MAX_FILE_SIZE = 25 * 1024 * 1024 # 25 MB

# Controlled Category Mapping
CATEGORY_MAP = {
    # Album covers / Cover arts
    'cover-arts': 'cover-arts',
    'cat_cover-arts': 'cover-arts',
    'cover arts': 'cover-arts',
    'cover-art': 'cover-arts',
    'album-covers': 'cover-arts',
    'album covers': 'cover-arts',
    'album-cover': 'cover-arts',
    
    # Graphic design / Posters
    'posters': 'posters',
    'poster-designs': 'posters',
    'cat_poster-designs': 'posters',
    'poster designs': 'posters',
    'poster-design': 'posters',
    'graphic-design': 'posters',
    'graphic design': 'posters',
    
    # Music promotions / Music videos
    'music-videos': 'music-videos',
    'cat_music-videos': 'music-videos',
    'music videos': 'music-videos',
    'music-video': 'music-videos',
    'music-promotions': 'music-videos',
    'music promotions': 'music-videos',
    
    # Video editing / Promotional edits
    'promotional-edits': 'promotional-edits',
    'cat_promotional-edits': 'promotional-edits',
    'promotional edits': 'promotional-edits',
    'promotional-edit': 'promotional-edits',
    'video-editing': 'promotional-edits',
    'video editing': 'promotional-edits',
    
    # Thumbnails
    'thumbnails': 'thumbnails',
    'cat_thumbnails': 'thumbnails',
    'thumbnail': 'thumbnails',
    
    # Illustrations / Edits / Title Cards / Other
    'illustrations': 'other',
    'illustration': 'other',
    'edits': 'other',
    'cat_edits': 'other',
    'title-cards': 'other',
    'cat_title-cards': 'other',
    'dispatches': 'other',
    'other': 'other'
}

def get_category_folder(category_key):
    """Normalize any category input to canonical assets subfolder."""
    if not category_key:
        return 'cover-arts'
    clean = str(category_key).strip().lower().replace('_', '-')
    return CATEGORY_MAP.get(clean, 'cover-arts')

def normalize_category_folder(category_key):
    return get_category_folder(category_key)

def is_allowed_file(filename, mime_type=None):
    """Validate file extension and MIME type."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    ext_ok = ext in ALLOWED_EXTENSIONS
    if mime_type:
        return ext_ok or (mime_type in ALLOWED_MIMES)
    return ext_ok

def sanitize_filename(raw_name):
    """
    Sanitizes user filename safely:
    'My Album Cover FINAL!!.PNG' -> 'my-album-cover-final.png'
    """
    if not raw_name:
        return f"artwork-{str(uuid.uuid4())[:8]}.jpg"
    
    name, ext = os.path.splitext(raw_name)
    ext = ext.lower().replace('.', '')
    if not ext:
        ext = 'jpg'
    
    # Keep alphanumeric, hyphen, underscore
    clean = re.sub(r'[^a-zA-Z0-9\-_]', '-', name)
    clean = re.sub(r'-+', '-', clean).strip('-').lower()
    if not clean:
        clean = f"artwork-{str(uuid.uuid4())[:8]}"
    return f"{clean}.{ext}"

def compute_sha256(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()

def get_unique_filename(category_folder, safe_name):
    """Avoid overwriting existing files by appending -2, -3 if needed."""
    local_dir = os.path.join(ASSETS_ROOT, category_folder)
    os.makedirs(local_dir, exist_ok=True)

    base, ext = os.path.splitext(safe_name)
    candidate = safe_name
    counter = 2

    # Check local folder
    while os.path.exists(os.path.join(local_dir, candidate)):
        candidate = f"{base}-{counter}{ext}"
        counter += 1

    return candidate

def upload_to_github(file_bytes, category_folder, filename):
    """
    Commit and upload asset directly to GitHub repo:
    assets/<category_folder>/<filename>
    """
    if not GITHUB_TOKEN:
        print("[GitHub Upload] Warning: GITHUB_TOKEN not set, skipping GitHub commit")
        return None

    path = f"assets/{category_folder}/{filename}"
    api_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    data = {
        "message": f"upload: add {filename} to assets/{category_folder}",
        "content": b64_content,
        "branch": GITHUB_BRANCH
    }

    # Check if file exists on GitHub to obtain sha for update
    sha = None
    try:
        check_req = urllib.request.Request(
            api_url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "dragxsy-portfolio-cms"
            }
        )
        with urllib.request.urlopen(check_req, timeout=10) as resp:
            existing = json.loads(resp.read().decode('utf-8'))
            sha = existing.get("sha")
    except Exception:
        pass

    if sha:
        data["sha"] = sha

    req = urllib.request.Request(
        api_url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "dragxsy-portfolio-cms"
        },
        method="PUT"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{path}"
            print(f"[GitHub Upload] Successfully committed to GitHub: {path}")
            return raw_url
    except Exception as e:
        print(f"[GitHub Upload] Error committing {path} to GitHub: {e}")
        return None

def process_and_store_image(file_storage, filename, category_key="cover-arts"):
    """
    Full validation and upload pipeline:
    1. Validates format and size <= 25MB
    2. Sanitizes filename safely
    3. Normalizes category to assets/<category>/
    4. Commits to GitHub repository
    5. Saves local copy in assets/<category>/
    6. Returns canonical path 'assets/<category>/<filename>'
    """
    file_bytes = file_storage.read()
    file_storage.seek(0)

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File size ({len(file_bytes) // (1024*1024)}MB) exceeds 25MB limit")

    if not is_allowed_file(filename):
        raise ValueError("Unsupported image format. Allowed: JPG, PNG, WEBP, GIF, SVG, MP4, WEBM")

    category_folder = get_category_folder(category_key)
    safe_name = sanitize_filename(filename)
    unique_name = get_unique_filename(category_folder, safe_name)

    # 1. Commit directly to GitHub repository
    github_raw_url = upload_to_github(file_bytes, category_folder, unique_name)

    # 2. Save local copy in assets/<category_folder>/
    local_dir = os.path.join(ASSETS_ROOT, category_folder)
    os.makedirs(local_dir, exist_ok=True)
    local_path = os.path.join(local_dir, unique_name)
    try:
        with open(local_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        print(f"[Storage] Note writing local file: {e}")

    # Canonical relative path for portfolio
    canonical_asset_path = f"assets/{category_folder}/{unique_name}"

    width, height = 800, 800
    ext = unique_name.rsplit('.', 1)[1].lower() if '.' in unique_name else 'jpg'
    if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
        except Exception:
            pass

    full_github_url = github_raw_url or f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}/{canonical_asset_path}"
    return {
        "id": "asset_" + str(uuid.uuid4())[:8],
        "filename": unique_name,
        "category": category_folder,
        "assetPath": canonical_asset_path,
        "image": canonical_asset_path,
        "cardUrl": canonical_asset_path,
        "originalUrl": canonical_asset_path,
        "optimizedUrl": canonical_asset_path,
        "thumbnailUrl": canonical_asset_path,
        "githubUrl": full_github_url,
        "width": width,
        "height": height,
        "sizeBytes": len(file_bytes),
        "hash": compute_sha256(file_bytes)
    }
