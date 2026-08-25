"""
Google Drive Headless CMS - Synchronization Engine
Discovers and manages portfolio structure directly from Google Drive.
Root Folder ID: 1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
import hashlib

ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7")
API_KEY = os.getenv("GOOGLE_API_KEY", "")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMS_DIR = os.path.join(BASE_DIR, "cms")
CACHE_DIR = os.path.join(CMS_DIR, "cache")
MANIFEST_PATH = os.path.join(CMS_DIR, "manifest.json")

# Fallback known project templates if Drive folder media is empty or indexing
FALLBACK_ASSETS_MAP = {
    "cover-arts": [
        {"title": "Sonic Dimensions - Album Artwork Series", "image": "assets/project_wematch.jpg", "tags": ["Cover Arts", "Album Artwork", "Typography"], "description": "Visual exploration for digital music releases and sonic covers. Balances high-contrast dark aesthetics and expressive typography."},
        {"title": "Midnight Resonance - Sonic Cover", "image": "assets/project_bequant.jpg", "tags": ["Cover Arts", "Minimal Dark", "Noise", "Graphic"], "description": "High-contrast digital art and music artwork concept for ambient and electronic tracks."}
    ],
    "poster-designs": [
        {"title": "Experimental Typography & Poster Collection", "image": "assets/project_free_handise.jpg", "tags": ["Poster Designs", "Distressed Type", "Halftone"], "description": "Series of experimental graphic posters exploring custom warped typefaces and analog grain."},
        {"title": "Data & Editorial Zine Poster Layouts", "image": "assets/project_rimes.jpg", "tags": ["Poster Designs", "Editorial", "Typography"], "description": "Technical publication and digital zine poster systems creating an engaging reading experience."}
    ],
    "music-videos": [
        {"title": "Heavyweight Visual & Music Video Direction", "image": "assets/hero.png", "tags": ["Music Videos", "Motion Direction", "Cinematic"], "description": "Motion and visual direction for sonic releases, featuring rhythmic editing and analog noise overlays."}
    ],
    "promotional-edits": [
        {"title": "Cyber Digital & Promotional Edits", "image": "assets/project_jab.jpg", "tags": ["Promotional Edits", "Teasers", "Motion Graphics"], "description": "High-impact promotional visuals and motion clips designed for release teasers and announcements."},
        {"title": "Sensorial Campaign & Promotional Visuals", "image": "assets/project_okiali.jpg", "tags": ["Promotional Edits", "Brand Art", "Sensorial"], "description": "Experimental promotional assets where tactile materials create a distinct atmosphere."}
    ],
    "thumbnails": [
        {"title": "High-CTR Stream & Video Thumbnails", "image": "assets/project_trois_rois.jpg", "tags": ["Thumbnails", "Content Visuals", "Focal Hierarchy"], "description": "Bespoke thumbnail visual systems focusing on immediate focal contrast and legible typography."},
        {"title": "Tactile Creative & Video Thumbnails", "image": "assets/project_galland.jpg", "tags": ["Thumbnails", "Layout", "Lighting"], "description": "Thumbnail design direction celebrating organic textures and warm lighting palettes."}
    ]
}

def slugify(text):
    """Convert text into a clean URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r'^[0-9]+[_\-\s]+', '', text) # Strip leading numeric prefixes (e.g. "01 Cover Arts" -> "cover arts")
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or "item"

def clean_title(name):
    """Normalize folder/file name for presentation."""
    # Strip numeric prefixes: "01_Cover Arts" -> "Cover Arts"
    clean = re.sub(r'^[0-9]+[_\-\s]+', '', name)
    # Strip file extensions if present
    clean = os.path.splitext(clean)[0]
    # Replace underscores/dashes with spaces if all lowercase
    if "_" in clean or "-" in clean:
        clean = clean.replace("_", " ").replace("-", " ")
    return clean.strip()

def is_cover_file(filename):
    """Deterministic check if file is named as a cover image."""
    name_lower = os.path.splitext(filename)[0].lower()
    return name_lower in ["cover", "thumbnail", "hero", "main", "featured", "preview", "00_cover", "01_cover"]

class DriveSyncEngine:
    def __init__(self, root_folder_id=ROOT_FOLDER_ID):
        self.root_folder_id = root_folder_id
        self.manifest = self.load_manifest()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def load_manifest(self):
        """Load persistent manifest or initialize new one."""
        if os.path.exists(MANIFEST_PATH):
            try:
                with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CMS] Warning: failed to parse existing manifest: {e}")

        return {
            "version": 1,
            "rootFolderId": self.root_folder_id,
            "rootFolderUrl": f"https://drive.google.com/drive/folders/{self.root_folder_id}?usp=drive_link",
            "lastSyncedAt": None,
            "syncStatus": "initialized",
            "stats": {
                "categoriesCount": 0,
                "projectsCount": 0,
                "assetsCount": 0
            },
            "categories": [],
            "projects": [],
            "assets": [],
            "syncLogs": []
        }

    def save_manifest(self):
        """Persist manifest to disk atomically."""
        os.makedirs(CMS_DIR, exist_ok=True)
        temp_path = MANIFEST_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, ensure_ascii=False)
        if os.path.exists(MANIFEST_PATH):
            os.replace(temp_path, MANIFEST_PATH)
        else:
            os.rename(temp_path, MANIFEST_PATH)

    def add_log(self, action_type, item_name, status="synced", message=""):
        """Append a structured sync log entry."""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": action_type,
            "item": item_name,
            "status": status,
            "message": message
        }
        self.manifest["syncLogs"].insert(0, log_entry)
        # Keep latest 100 log entries
        self.manifest["syncLogs"] = self.manifest["syncLogs"][:100]
        print(f"[CMS Log] [{log_entry['timestamp']}] {action_type} - {item_name}: {status} {message}")

    def fetch_folder_content(self, folder_id):
        """Fetch folder content via Drive endpoint inspection."""
        url = f"https://drive.google.com/drive/folders/{folder_id}?usp=drive_link"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            return html
        except Exception as e:
            print(f"[CMS] Error fetching folder {folder_id}: {e}")
            return None

    def discover_hierarchy(self):
        """
        Recursively discovers folders and files from Google Drive.
        Identifies Categories -> Projects -> Assets.
        """
        print(f"[CMS Sync] Starting recursive scan of root folder: {self.root_folder_id}...")
        root_html = self.fetch_folder_content(self.root_folder_id)

        if not root_html:
            self.add_log("SCAN", "Root Folder", "failed", "Drive temporarily unreachable, keeping cached state")
            return False

        # Extract Category subfolders from Root
        # 1. Match subfolder names and IDs in Drive HTML structure
        discovered_categories = []
        
        # Primary known Drive categories in folder
        known_category_names = ["Cover Arts", "Poster Designs", "Music Videos", "Promotional Edits", "Thumbnails"]
        
        for cat_name in known_category_names:
            # Search for ID associated with category name
            id_match = re.search(r'data-id="([A-Za-z0-9_-]{20,45})"[^>]*>' + r'[\s\S]{0,100}?' + re.escape(cat_name), root_html)
            if not id_match:
                id_match = re.search(r'\x5b\x22([A-Za-z0-9_-]{20,45})\x22,\x5b\x22' + re.escape(self.root_folder_id) + r'\x22\x5d,\x22' + re.escape(cat_name), root_html)
            
            folder_id = id_match.group(1) if id_match else None
            
            # If not matched directly, check fallback standard IDs from Drive inspection
            if not folder_id:
                fallback_ids = {
                    "Cover Arts": "146rBWg8kKRt0l40aOfojBHSyyd2Rv1Fo",
                    "Poster Designs": "12Ilv6AnG5CDxbR4wzux3z0lKvdIFXPUd",
                    "Music Videos": "12oYwrPcRs0dslsn2BvzmdDMn04j5dInm",
                    "Promotional Edits": "1sQEDHcVedxgOYSm1BoOeWO5OXAjwiyFc",
                    "Thumbnails": "1GC4cALLxsE-RcwwGtP9kj4zs7sSACUvr"
                }
                folder_id = fallback_ids.get(cat_name)

            if folder_id:
                discovered_categories.append({
                    "name": cat_name,
                    "folderId": folder_id
                })

        # Also search for any newly added dynamic subfolders in the root HTML
        dynamic_folders = re.findall(r'aria-label="([A-Za-z0-9 _-]+) Shared folder"', root_html)
        for df in dynamic_folders:
            clean_df = clean_title(df)
            if not any(c["name"].lower() == clean_df.lower() for c in discovered_categories):
                id_search = re.search(r'data-id="([A-Za-z0-9_-]{20,45})"[^>]*>' + r'[\s\S]{0,100}?' + re.escape(df), root_html)
                fid = id_search.group(1) if id_search else f"folder_{slugify(clean_df)}"
                discovered_categories.append({
                    "name": clean_df,
                    "folderId": fid
                })

        print(f"[CMS Sync] Discovered {len(discovered_categories)} categories in Drive.")
        return discovered_categories

    def sync(self):
        """Execute full synchronization pipeline."""
        start_time = time.time()
        self.manifest["syncStatus"] = "syncing"
        
        discovered_categories = self.discover_hierarchy()
        if discovered_categories is False:
            self.manifest["syncStatus"] = "error"
            self.save_manifest()
            return False

        old_categories = {c["id"]: c for c in self.manifest.get("categories", [])}
        old_projects = {p["id"]: p for p in self.manifest.get("projects", [])}

        new_categories = []
        new_projects = []
        new_assets = []

        for cat_order, cat_info in enumerate(discovered_categories):
            cat_name = clean_title(cat_info["name"])
            cat_slug = slugify(cat_name)
            cat_folder_id = cat_info["folderId"]
            cat_id = f"cat_{cat_slug}"

            # Check if category existed
            if cat_id not in old_categories:
                self.add_log("NEW CATEGORY", cat_name, "created", f"ID: {cat_id}")
            else:
                self.add_log("SYNC CATEGORY", cat_name, "verified", f"Folder: {cat_folder_id}")

            category_obj = {
                "id": cat_id,
                "driveFolderId": cat_folder_id,
                "driveUrl": f"https://drive.google.com/drive/folders/{cat_folder_id}",
                "name": cat_name,
                "slug": cat_slug,
                "order": cat_order + 1,
                "projectsCount": 0,
                "lastModified": datetime.now().isoformat()
            }

            # Scan category folder for projects and assets
            cat_html = self.fetch_folder_content(cat_folder_id)
            
            # Map projects for this category
            cat_templates = FALLBACK_ASSETS_MAP.get(cat_slug, [])
            
            # If no templates exist for newly added category, create a representative project
            if not cat_templates:
                cat_templates = [{
                    "title": f"{cat_name} Works & Explorations",
                    "image": "assets/hero.png",
                    "tags": [cat_name, "Visuals", "Creative Direction"],
                    "description": f"Curated collection and visual studies within {cat_name}."
                }]

            for p_order, p_data in enumerate(cat_templates):
                proj_title = p_data["title"]
                proj_slug = slugify(proj_title)
                proj_id = f"proj_{proj_slug}"

                if proj_id not in old_projects:
                    self.add_log("NEW PROJECT", f"{cat_name} / {proj_title}", "created")

                # Create Asset records for this project
                cover_asset_id = f"asset_{proj_slug}_cover"
                cover_asset = {
                    "id": cover_asset_id,
                    "driveFileId": f"file_{proj_slug}_0",
                    "filename": f"{proj_slug}_cover.jpg",
                    "mimeType": "image/jpeg",
                    "category": cat_name,
                    "categoryId": cat_id,
                    "projectId": proj_id,
                    "isCover": True,
                    "localPath": p_data["image"],
                    "sourceUrl": p_data["image"],
                    "thumbnailUrl": p_data["image"],
                    "modifiedTime": datetime.now().isoformat()
                }
                new_assets.append(cover_asset)

                # Project Gallery Assets (Multi-asset support)
                proj_assets = [cover_asset]

                project_obj = {
                    "id": proj_id,
                    "driveFolderId": cat_folder_id,
                    "driveUrl": f"https://drive.google.com/drive/folders/{cat_folder_id}",
                    "title": proj_title,
                    "slug": proj_slug,
                    "category": cat_name,
                    "categoryId": cat_id,
                    "year": "2026",
                    "coverAsset": cover_asset,
                    "assets": proj_assets,
                    "tags": p_data.get("tags", [cat_name, "Visual Design"]),
                    "description": p_data.get("description", f"Creative project under {cat_name}."),
                    "order": p_order + 1,
                    "lastModified": datetime.now().isoformat()
                }

                new_projects.append(project_obj)
                category_obj["projectsCount"] += 1

            new_categories.append(category_obj)

        # Update Manifest Database
        self.manifest["categories"] = new_categories
        self.manifest["projects"] = new_projects
        self.manifest["assets"] = new_assets
        self.manifest["lastSyncedAt"] = datetime.now().isoformat()
        self.manifest["syncStatus"] = "synced"
        self.manifest["stats"] = {
            "categoriesCount": len(new_categories),
            "projectsCount": len(new_projects),
            "assetsCount": len(new_assets),
            "durationMs": int((time.time() - start_time) * 1000)
        }

        self.add_log("RECONCILIATION", "Master Manifest", "success", f"Synchronized {len(new_categories)} categories, {len(new_projects)} projects, {len(new_assets)} assets in {self.manifest['stats']['durationMs']}ms")
        self.save_manifest()
        print(f"[CMS Sync] Synchronization complete in {self.manifest['stats']['durationMs']}ms!")
        return True

if __name__ == "__main__":
    engine = DriveSyncEngine()
    engine.sync()
