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

## 📁 Directory Structure & Companion Setup

Career Cockpit is designed with a **flexible, loosely-coupled architecture**:

* **Standalone Notion Triage Mode:** If you only need to inspect, search, filter, and triage your Notion Discovery Inbox or advance application stages in your Kanban tracker, you **only need this repository** and your `.env` Notion credentials.
* **Autonomous Scraping & Profile Tuning Mode:** To run the scraper directly from the GUI (**`▶ Run Job Scout`**) or edit your candidate criteria (**`⚙️ Profile`**), the companion engine [**`job-discovery-inbox`**](https://github.com/AhmedKhalifa3/job-discovery-inbox) is required.

### Recommended Workspace Layout

```text
Projects/Personal/
├── career-dashboard-gui/              # 💼 Desktop GUI Application (This Repository)
│   ├── app.py                         # Main CustomTkinter UI (navigation, cards, pagination, modals)
│   ├── backend.py                     # Notion Client API, scout subprocess controller, data sync
│   ├── run.sh                         # Desktop launcher script (activates .venv and launches app)
│   ├── install_desktop_app.sh         # Native Linux .desktop launcher installer for Ubuntu / GNOME
│   ├── build_binary.sh                # Standalone binary compiler using PyInstaller
│   ├── requirements.txt               # GUI Python dependencies (customtkinter, notion-client, pyyaml)
│   ├── .env                           # Notion API token and database IDs
│   ├── .env.example                   # Example environment configuration template
│   └── assets/
│       └── icon.png                   # Application icon for dock, window, and desktop launcher
│
└── job-discovery-inbox/               # 🔎 Scraper & Candidate Engine (Companion Repository)
    ├── scout.py                       # Autonomous search engine (ATS dorks & API feeds)
    ├── profile.yaml                   # Candidate criteria (roles, skills, locations, negative keywords)
    ├── config.py                      # Search queries, domain filters, and platform configs
    ├── discovered_jobs.json           # Local staging file for freshly discovered leads
    ├── seen_jobs.json                 # URL deduplication cache
    └── .venv/                         # Scraper virtual environment
```

### How to Clone with the Scraper Engine

> [!TIP]
> **Option A (Recommended — All 4 Suite Tools):**  
> Clone the master umbrella repository [**`autonomous-career-suite`**](https://github.com/AhmedKhalifa3/autonomous-career-suite), which automatically clones the GUI, scraper, FastMCP server, and Overleaf resume compiler side-by-side:
> ```bash
> git clone --recurse-submodules https://github.com/AhmedKhalifa3/autonomous-career-suite.git
> cd autonomous-career-suite && ./quickstart.sh
> ```

> **Option B (Manual Side-by-Side Clone):**  
> Clone both repositories into the same folder:
> ```bash
> git clone https://github.com/AhmedKhalifa3/career-dashboard-gui.git
> git clone https://github.com/AhmedKhalifa3/job-discovery-inbox.git
> ```

> **Option C (Custom Folder or Subfolder):**  
> If you place `job-discovery-inbox` inside `career-dashboard-gui/` or any custom path, set `SCOUT_PROJECT_PATH` in `.env`:
> ```env
> SCOUT_PROJECT_PATH=/path/to/job-discovery-inbox
> ```

---

## ⚡ Quickstart & Installation

### 1. Prerequisites

Ensure you have Python 3.10+ installed with `tkinter` support (on Ubuntu: `sudo apt install python3-tk`).

### 2. Setup Virtual Environment

```bash
cd ~/Projects/Personal/career-dashboard-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch the Application

```bash
cd ~/Projects/Personal/career-dashboard-gui
./run.sh
```

### 4. Install as a Native Linux Desktop App (Ubuntu / GNOME)

To integrate Career Cockpit directly into your Ubuntu Application Menu and Dock (with app icon and keyboard search):

```bash
cd ~/Projects/Personal/career-dashboard-gui
./install_desktop_app.sh
```

* Hit the **Super (Windows)** key, type **Career Cockpit**, and press **Enter** to open.
* Right-click the app in your Ubuntu Dock and click **"Pin to Dash" / "Add to Favorites"**!

### 5. Build a Standalone Executable Binary (PyInstaller)

To compile the entire application and its dependencies into a standalone binary:

```bash
cd ~/Projects/Personal/career-dashboard-gui
./build_binary.sh
```

The compiled binary will be placed at `dist/career-cockpit/career-cockpit`.

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
