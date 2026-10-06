# 💼 Career Cockpit — Autonomous Job Scout & Notion GUI Dashboard

> **A modern, dark-mode desktop GUI built with Python and CustomTkinter to control your autonomous job discovery scraper, triage incoming leads, and manage your Notion Discovery Inbox with one-click actions.**

---

## 🌟 Key Features

* 🚀 **Scout Controller**: Trigger fresh ATS scrapers (`24h`, `week`, `any`) across specific categories (`all`, `werkstudent`, `backend`, `ai_agent`, etc.) directly from the GUI with Force Rescan controls.
* ⚡ **High-Performance Architecture**:
  * **Ultra-Fast Paginated Rendering**: Renders 15 cards per page in <25ms, eliminating Tkinter UI lag and widget overload.
  * **Debounced Search (220ms)**: Smooth, instant typing with zero UI freezing or stuttering.
  * **60 FPS Throttled Console**: Log buffer batches stdout lines to maintain buttery responsiveness during heavy scraping.
* 📊 **Dual Database Mode (Discovery + Active Tracker)**:
  * **`📥 Discovery Inbox`**: Triage incoming scouted leads from Notion Discovery DB.
  * **`🆕 Newly Scouted (Local)`**: Review leads in local staging before pushing to Notion.
  * **`📊 Active Applications`**: Track your live application pipeline (`Applied`, `Screening`, `Interview`, `Offer`, `Rejected`, `Wishlist`) from Notion Job Tracker DB!
* 🚀 **One-Click Promotion to Application**:
  * Instantly promote approved leads from Discovery directly into the `Job Applications` Notion tracker.
* 👁️ **Job Details Inspect Modal**:
  * Open full job descriptions, match score breakdowns, role requirements, copyable URLs, and quick-action buttons in an elegant floating modal dialog.
* ⚙️ **In-GUI Search Profile Editor**:
  * View and update `target_roles`, `skills`, `locations`, and negative filters in `profile.yaml` without editing raw code.
* 🎯 **Smart Row Actions & Stage Advance**:
  * Advance application stages directly from dropdown menus on application cards.
  * One-click Approve, Dismiss, Trash, and Open in Browser.
* 🧹 **Bulk Maintenance**:
  * **`Clean All Dismissed`**: One-click bulk archival moving all dismissed job postings directly to Notion Trash.
  * **`Refresh All Notion Data`**: Instant parallel sync of both Discovery and Tracker databases.

---

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────────┐
│         💼 Career Cockpit Desktop GUI (app.py)         │
│         • CustomTkinter Modern Dark Theme              │
│         • Multi-threaded background tasks              │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
       Subprocess Streaming        REST API Calls
                │                        │
                ▼                        ▼
┌───────────────────────────────┐ ┌──────────────────────┐
│  job_discovery_inbox/scout.py │ │  Notion API Client   │
│  • Precision ATS dorks        │ │  • Leads retrieval   │
│  • Dynamic profile.yaml       │ │  • Status update     │
│  • Location & Relocation gate │ │  • Lead trash        │
│  • Pushes matches to Notion   │ │  • Bulk cleanup      │
└───────────────────────────────┘ └──────────────────────┘
```

---

## ⚡ Quickstart & Standalone App

### 1. Requirements

Ensure you have Python 3.10+ installed with `tkinter` support.

### 2. Launch the Dashboard

```bash
cd ~/Projects/Personal/career-dashboard-gui
./run.sh
```

### 3. Install as a Native Linux Desktop App (Ubuntu / GNOME)

To integrate Career Cockpit directly into your Ubuntu Application Menu and Dock (with app icon and keyboard search):

```bash
cd ~/Projects/Personal/career-dashboard-gui
./install_desktop_app.sh
```

* Hit the **Super (Windows)** key, type **Career Cockpit**, and press **Enter** to open.
* Right-click the app in your Ubuntu Dock and click **"Pin to Dash" / "Add to Favorites"**!

### 4. Build a Standalone Executable Binary (PyInstaller)

To compile the entire application and its dependencies into a standalone binary:

```bash
cd ~/Projects/Personal/career-dashboard-gui
./build_binary.sh
```

The compiled binary will be placed at `dist/career-cockpit/career-cockpit`.
python app.py
```

---

## ⚙️ Configuration (`.env`)

The application automatically reads from `.env` in this folder, or falls back to your existing `.env` files in `../notion-tracker-mcp` or `../job_discovery_inbox`.

```env
# Notion API Configuration
NOTION_API_KEY=ntn_your_notion_integration_token_here
NOTION_DISCOVERED_JOBS_DB_ID=03c69cc9897c4a269a8e2123f92266e7
NOTION_JOB_TRACKER_DB_ID=694a0ed9779a4556bd0c43e98746ab7e

# Optional: Custom path to job_discovery_inbox
SCOUT_PROJECT_PATH=../job_discovery_inbox
```

---

## 📄 License

MIT License. Free to customize for your own autonomous career hunt!
