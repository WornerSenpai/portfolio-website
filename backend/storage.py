"""
Media Storage & Image Processing Pipeline for Cloud CMS
Directly uploads and commits assets to categorized GitHub subfolders:
portfolio-assets/<category-slug>/<filename>
Provides immutable GitHub Raw CDN URLs and instant Base64 fallbacks.
"""

import os
import io
import uuid
import base64
import hashlib
import json
import urllib.request
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "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")
GITHUB_REPO = "WornerSenpai/portfolio-website"

if os.getenv("VERCEL"):
    UPLOADS_DIR = "/tmp/uploads"
else:
    UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

MEDIA_DIR = os.path.join(UPLOADS_DIR, "media")
OPTIMIZED_DIR = os.path.join(UPLOADS_DIR, "optimized")
CARDS_DIR = os.path.join(UPLOADS_DIR, "cards")
THUMBS_DIR = os.path.join(UPLOADS_DIR, "thumbnails")

for d in [MEDIA_DIR, OPTIMIZED_DIR, CARDS_DIR, THUMBS_DIR]:
    os.makedirs(d, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp4', 'mov', 'webm'}
ALLOWED_MIMES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
    'video/mp4', 'video/quicktime', 'video/webm'
}
MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB

def is_allowed_file(filename, mime_type):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS or mime_type in ALLOWED_MIMES

def compute_sha256(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()

def upload_to_github_category(file_bytes, category_slug, filename):
    """
    Commit and upload asset directly into categorized GitHub folder:
    portfolio-assets/<category_slug>/<filename>
    Returns high-speed raw GitHub CDN URL.
    """
    if not category_slug:
        category_slug = "cover-arts"
        
    path = f"portfolio-assets/{category_slug}/{filename}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    
    b64_content = base64.b64encode(file_bytes).decode('utf-8')
    data = {
        "message": f"upload: add {filename} to {category_slug}",
        "content": b64_content,
        "branch": "main"
    }
    
    # Check if file exists on GitHub to get SHA if updating
    sha = None
    try:
        check_req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "dragxsy-cms"
            }
        )
        with urllib.request.urlopen(check_req) as resp:
            existing = json.loads(resp.read().decode('utf-8'))
            sha = existing.get("sha")
    except Exception:
        pass
        
    if sha:
        data["sha"] = sha

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "dragxsy-cms"
        },
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req) as resp:
            raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{path}"
            print(f"[GitHub Upload] Successfully committed asset to: {path}")
            return raw_url
    except Exception as e:
        print(f"[GitHub Upload] Note: could not commit directly via API ({e}), using local and Data URL fallback")
        return None

def process_and_store_image(file_storage, filename, category_slug="cover-arts"):
    file_bytes = file_storage.read()
    file_storage.seek(0)
    
    file_hash = compute_sha256(file_bytes)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    unique_id = str(uuid.uuid4())[:10]
    safe_filename = f"{unique_id}.{ext}"

    # 1. Upload to categorized GitHub directory
    github_url = upload_to_github_category(file_bytes, category_slug, safe_filename)

    # 2. Also save to local repository portfolio-assets folder if on local machine
    local_cat_dir = os.path.join(BASE_DIR, "portfolio-assets", category_slug)
    os.makedirs(local_cat_dir, exist_ok=True)
    local_cat_path = os.path.join(local_cat_dir, safe_filename)
    try:
        with open(local_cat_path, "wb") as f:
            f.write(file_bytes)
    except Exception:
        pass

    width, height = 800, 800
    data_url = ""

    # 3. Create lightweight Base64 Data URL
    if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                if img.mode in ('RGBA', 'LA') and ext in ['jpg', 'jpeg']:
                    img = img.convert('RGB')

                card_img = img.copy()
                card_img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                if ext == 'png' and img.mode == 'RGBA':
                    card_img.save(buffer, format="PNG", optimize=True)
                    mime = "image/png"
                else:
                    if card_img.mode != 'RGB':
                        card_img = card_img.convert('RGB')
                    card_img.save(buffer, format="JPEG", quality=82, optimize=True)
                    mime = "image/jpeg"
                
                b64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                data_url = f"data:{mime};base64,{b64_data}"
        except Exception:
            b64_data = base64.b64encode(file_bytes).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{b64_data}"
    else:
        b64_data = base64.b64encode(file_bytes).decode('utf-8')
        data_url = f"data:video/mp4;base64,{b64_data}"

    # Best URL: Prefer GitHub Raw CDN if available, else Data URL
    final_url = github_url or data_url

    return {
        "id": "asset_" + unique_id,
        "filename": filename,
        "githubUrl": github_url,
        "dataUrl": data_url,
        "originalUrl": final_url,
        "optimizedUrl": final_url,
        "cardUrl": final_url,
        "thumbnailUrl": final_url,
        "width": width,
        "height": height,
        "sizeBytes": len(file_bytes),
        "hash": file_hash
    }
