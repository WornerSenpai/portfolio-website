# dragxsy - Google Drive Powered Headless CMS

> **CREATE -> ORGANISE -> FORGET.**
> Manage your entire creative portfolio directly by organizing files and folders in Google Drive. Zero code changes required to add, update, rename, or reorganize artwork.

---

## 🏗️ Architecture

```
GOOGLE DRIVE (Folder: 1B9uH8D5bfhEK99DaApeL7fVYUcbrZbF7)
  │
  ├── Cover Arts/
  ├── Poster Designs/
  ├── Music Videos/
  ├── Promotional Edits/
  └── Thumbnails/
       │
       ▼ (Drive API / Change Webhook / Scheduled Reconciliation)
┌────────────────────────────────────────────────────────┐
│                   SYNC AGENT (Backend)                 │
│  - Folder Hierarchy Scanner (Recursive Discovery)     │
│  - Change Detector (Create, Update, Rename, Move, Del)│
│  - Deterministic Cover Image Selector                  │
│  - Asset Cache & Optimization Pipeline                 │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             PORTFOLIO CMS DATABASE (Manifest)          │
│  - cms/manifest.json (Categories, Projects, Assets)    │
│  - Versioned schema with file IDs & Checksums          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                  CONTENT API & SERVER                  │
│  - GET  /api/portfolio      GET /api/categories        │
│  - GET  /api/projects/:slug GET /api/assets/:id        │
│  - POST /api/sync           POST /api/webhook          │
│  - GET  /admin/cms (Protected CMS Dashboard)           │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                 FRONTEND PORTFOLIO                     │
│  - 3D Interactive WebGL Cylinder (Dynamic from CMS)    │
│  - Dynamic Category Filter Pills                       │
│  - Dynamic Project Cards & Full Media Galleries        │
│  - Offline / Cached Fallback Support                   │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Install & Start Server
```bash
pip install -r requirements.txt
python server.py
```
- **Portfolio Website**: [http://localhost:5000](http://localhost:5000)
- **CMS Admin Dashboard**: [http://localhost:5000/admin/cms](http://localhost:5000/admin/cms)
- **Content API**: [http://localhost:5000/api/portfolio](http://localhost:5000/api/portfolio)

---

## 📁 How to Manage Content in Google Drive

### 1. Adding a New Category
Simply create a folder in your Google Drive root folder:
```
Drive/
└── 3D Renders/
```
The Sync Engine will automatically create the `3D Renders` category tab on your website.

### 2. Adding a New Project
Create a project folder inside any category folder:
```
Drive/
└── Poster Designs/
    └── Acid Grain Vol 2/
        ├── cover.jpg          <-- Priority cover image
        ├── gallery_01.jpg
        └── gallery_02.jpg
```

### 3. Setting a Cover Image (Deterministic Priority)
The CMS selects the card image using this priority:
1. File named `cover.*`, `thumbnail.*`, `hero.*`, `main.*`, or `featured.*`
2. Otherwise the first sorted image file

### 4. Optional Metadata File (`_metadata.json` or `_project.json`)
You can optionally place a `_metadata.json` file inside any project folder:
```json
{
  "title": "Acid Grain Vol 2",
  "year": "2026",
  "tags": ["Poster", "Brutalist", "Grain"],
  "description": "Experimental typographic poster series exploring analog distortion."
}
```
*(Optional: If no metadata file exists, the CMS automatically generates clean titles from folder and file names).*

---

## ⚡ Synchronization & Automation

### 1. On-Demand Sync
- Click **"Sync Google Drive Now"** in the [Admin CMS Dashboard](http://localhost:5000/admin/cms).
- Or press **`Ctrl + Shift + C`** anywhere on the portfolio website.
- Or make a `POST` request to `/api/sync`.

### 2. Webhook Integration (Real-Time Push Notifications)
Configure Google Workspace / Google Drive push notifications to send events to:
```
POST https://yourdomain.com/api/webhook
```
When Google Drive sends `add`, `update`, `trash`, or `change` events, the sync engine updates the CMS immediately.

### 3. Periodic Background Reconciliation
The server runs an automated background reconciliation thread every `SYNC_INTERVAL_HOURS` (default 3 hours) to ensure zero missed updates.
