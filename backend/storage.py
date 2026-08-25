"""
Media Storage & Image Processing Pipeline for Android CMS
Validates media formats, computes SHA-256 hashes, generates responsive thumbnails.
Supports local server and Vercel serverless /tmp writable storage.
"""

import os
import uuid
import hashlib
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    """Validate file extension and MIME type."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_EXTENSIONS or mime_type in ALLOWED_MIMES

def compute_sha256(file_bytes):
    """Compute SHA-256 hash for duplicate detection."""
    return hashlib.sha256(file_bytes).hexdigest()

def process_and_store_image(file_storage, filename):
    """
    Save original media and generate responsive variants.
    """
    file_bytes = file_storage.read()
    file_storage.seek(0)
    
    file_hash = compute_sha256(file_bytes)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    unique_id = str(uuid.uuid4())[:12]
    safe_filename = f"{unique_id}.{ext}"

    for d in [MEDIA_DIR, OPTIMIZED_DIR, CARDS_DIR, THUMBS_DIR]:
        os.makedirs(d, exist_ok=True)

    original_path = os.path.join(MEDIA_DIR, safe_filename)
    optimized_path = os.path.join(OPTIMIZED_DIR, safe_filename)
    card_path = os.path.join(CARDS_DIR, safe_filename)
    thumb_path = os.path.join(THUMBS_DIR, safe_filename)

    # Save original
    with open(original_path, "wb") as f:
        f.write(file_bytes)

    width, height = 0, 0

    # Process image responsive variants with Pillow if image
    if ext in ['jpg', 'jpeg', 'png', 'webp']:
        try:
            with Image.open(original_path) as img:
                width, height = img.size
                if img.mode in ('RGBA', 'LA') and ext in ['jpg', 'jpeg']:
                    img = img.convert('RGB')

                # 1. Optimized Web (max 1600px)
                opt_img = img.copy()
                opt_img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                opt_img.save(optimized_path, quality=85, optimize=True)

                # 2. Card Preview (max 800px)
                card_img = img.copy()
                card_img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                card_img.save(card_path, quality=80, optimize=True)

                # 3. Thumbnail (max 300px)
                thumb_img = img.copy()
                thumb_img.thumbnail((300, 300), Image.Resampling.LANCZOS)
                thumb_img.save(thumb_path, quality=75, optimize=True)
        except Exception as e:
            print(f"[Storage] Warning processing image variants: {e}")
            with open(optimized_path, "wb") as f: f.write(file_bytes)
            with open(card_path, "wb") as f: f.write(file_bytes)
            with open(thumb_path, "wb") as f: f.write(file_bytes)
    else:
        # Video / fallback
        with open(optimized_path, "wb") as f: f.write(file_bytes)
        with open(card_path, "wb") as f: f.write(file_bytes)
        with open(thumb_path, "wb") as f: f.write(file_bytes)

    return {
        "id": "asset_" + unique_id,
        "filename": filename,
        "originalUrl": f"/uploads/media/{safe_filename}",
        "optimizedUrl": f"/uploads/optimized/{safe_filename}",
        "cardUrl": f"/uploads/cards/{safe_filename}",
        "thumbnailUrl": f"/uploads/thumbnails/{safe_filename}",
        "width": width,
        "height": height,
        "sizeBytes": len(file_bytes),
        "hash": file_hash
    }
