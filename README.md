# 💼 Career Cockpit — Autonomous Job Scout & Notion GUI Dashboard

> **A modern, dark-mode desktop GUI built with Python and CustomTkinter to control your autonomous job discovery scraper, triage incoming leads, and manage your Notion Discovery Inbox with one-click actions.**

---

## 🌟 Key Features

* 🚀 **Scout Controller**: Trigger fresh ATS scrapers (`24h`, `week`, `any`) across specific categories (`all`, `werkstudent`, `backend`, `ai_agent`, etc.) directly from the GUI.
* 🛑 **Live Process Controls**: Stop running scrapers anytime with one-click process termination.
* 📡 **Live Streaming Console**: Real-time terminal log embedded inside the app showing live search dorks, scraping progress, and Notion API status updates.
* 📊 **Live Metric Cards**: Instant counters for **Total Leads**, **New (Awaiting Review)**, **Approved**, and **Dismissed**.
* 🔍 **Smart Search & Triage Tabs**:
  * Filter leads instantly between **`New`**, **`Approved`**, **`Dismissed`**, or **`All`**.
  * Real-time search box filtering across Company, Role, Location, and Notes.
* 🎯 **One-Click Row Actions**:
  * **`✅ Approve`**: Promotes a lead to `Approved` in Notion.
  * **`❌ Dismiss`**: Flags a lead as `Dismissed` in Notion.
  * **`🗑️ Trash`**: Archives the page directly to Notion Trash.
  * **`🔗 Open Job Link`**: Opens the target job application page in your default browser.
* 🧹 **Bulk Maintenance**:
  * **`Clean All Dismissed`**: One-click bulk archival moving all dismissed job postings directly to Notion Trash.
  * **`Refresh Leads`**: Instant sync with your latest Notion database state.

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

## ⚡ Quickstart

### 1. Requirements

Ensure you have Python 3.10+ installed with `tkinter` support.

### 2. Launch the Dashboard

From the project root:

```bash
cd ~/Projects/Personal/career-dashboard-gui
./run.sh
```

Or manually:

```bash
cd ~/Projects/Personal/career-dashboard-gui
source .venv/bin/activate
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
