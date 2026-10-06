"""
Backend controller for Career Dashboard GUI.
Handles Notion API operations, Scout subprocess execution, and local-to-Notion sync.
"""

import os
import sys
import json
import signal
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables (checking local, then parent/peer project folders)
load_dotenv()
if not os.getenv("NOTION_API_KEY"):
    for peer_env in [
        "../.env",
        "../notion-tracker-mcp/.env",
        "../job_discovery_inbox/.env",
        "../job-discovery-inbox/.env",
    ]:
        if os.path.exists(peer_env):
            load_dotenv(peer_env)
            break

def clean_id(raw_id: str) -> str:
    if not raw_id:
        return ""
    return raw_id.split("?")[0].rstrip("/").split("/")[-1].replace("-", "")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DISCOVERED_JOBS_DB_ID = clean_id(os.getenv("NOTION_DISCOVERED_JOBS_DB_ID", ""))
NOTION_JOB_TRACKER_DB_ID = clean_id(
    os.getenv("NOTION_JOB_TRACKER_DB_ID", "") or os.getenv("NOTION_DATABASE_ID", "")
)

# Path to job_discovery_inbox
def _find_scout_dir() -> str:
    override = os.getenv("SCOUT_PROJECT_PATH")
    if override and os.path.exists(override):
        return os.path.abspath(override)
    candidates = [
        os.path.join(os.path.dirname(__file__), "job-discovery-inbox"),
        os.path.join(os.path.dirname(__file__), "job_discovery_inbox"),
        os.path.join(os.path.dirname(__file__), "../job_discovery_inbox"),
        os.path.join(os.path.dirname(__file__), "../job-discovery-inbox"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[2])

DEFAULT_SCOUT_DIR = _find_scout_dir()

_SCHEMA_CACHE: Dict[str, Any] = {}
_ACTIVE_SCOUT_PROC: Optional[subprocess.Popen] = None
_SCOUT_LOCK = threading.Lock()

def get_notion_client() -> Client:
    api_key = os.getenv("NOTION_API_KEY", NOTION_API_KEY)
    if not api_key:
        raise ValueError("NOTION_API_KEY is not set. Please configure .env.")
    return Client(auth=api_key)

def get_discovery_db_id() -> str:
    db_id = clean_id(os.getenv("NOTION_DISCOVERED_JOBS_DB_ID", NOTION_DISCOVERED_JOBS_DB_ID))
    if not db_id:
        raise ValueError("NOTION_DISCOVERED_JOBS_DB_ID is not configured.")
    return db_id

def get_tracker_db_id() -> str:
    db_id = clean_id(
        os.getenv("NOTION_JOB_TRACKER_DB_ID", NOTION_JOB_TRACKER_DB_ID)
        or os.getenv("NOTION_DATABASE_ID", "")
    )
    if not db_id:
        raise ValueError("NOTION_JOB_TRACKER_DB_ID (or NOTION_DATABASE_ID) is not configured.")
    return db_id

def inspect_database_schema(client: Client, db_id: str) -> Dict[str, Any]:
    global _SCHEMA_CACHE
    if db_id in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[db_id]

    db = client.databases.retrieve(database_id=db_id)
    props = db.get("properties") or {}
    data_source_id = None

    data_sources = db.get("data_sources") or []
    if not props and data_sources:
        ds_info = data_sources[0]
        data_source_id = ds_info.get("id")
        if data_source_id:
            ds = client.data_sources.retrieve(data_source_id=data_source_id)
            props = ds.get("properties") or {}

    schema = {
        "data_source_id": data_source_id,
        "title_prop": None,
        "role_prop": None,
        "status_prop": None,
        "status_type": "select",
        "url_prop": None,
        "location_prop": None,
        "score_prop": None,
        "category_prop": None,
        "notes_prop": None,
        "date_prop": None,
    }

    for name, data in props.items():
        prop_type = data.get("type")
        lower_name = name.lower()

        if prop_type == "title" and not schema["title_prop"]:
            schema["title_prop"] = name
        elif prop_type == "url" and not schema["url_prop"]:
            schema["url_prop"] = name
        elif prop_type in ("select", "status") and not schema["status_prop"] and any(k in lower_name for k in ["status", "stage", "state"]):
            schema["status_prop"] = name
            schema["status_type"] = prop_type
        elif prop_type == "number" and "score" in lower_name:
            schema["score_prop"] = name
        elif prop_type in ("select", "rich_text") and "category" in lower_name:
            schema["category_prop"] = name
        elif prop_type in ("rich_text", "select") and not schema["role_prop"] and any(k in lower_name for k in ["role", "position", "title", "job"]):
            schema["role_prop"] = name
        elif prop_type in ("rich_text", "select") and not schema["location_prop"] and any(k in lower_name for k in ["location", "place"]):
            schema["location_prop"] = name
        elif prop_type == "rich_text" and not schema["notes_prop"] and "note" in lower_name:
            schema["notes_prop"] = name
        elif prop_type == "date" and not schema["date_prop"]:
            schema["date_prop"] = name

    # Fallbacks
    if not schema["title_prop"]:
        for name, data in props.items():
            if data.get("type") == "title":
                schema["title_prop"] = name
                break

    if not schema["status_prop"]:
        for name, data in props.items():
            if data.get("type") in ("select", "status"):
                schema["status_prop"] = name
                schema["status_type"] = data.get("type")
                break

    _SCHEMA_CACHE[db_id] = schema
    return schema

def _get_page_prop_text(page: Dict[str, Any], prop_name: Optional[str]) -> str:
    if not prop_name:
        return ""
    props = page.get("properties", {})
    p = props.get(prop_name, {})
    p_type = p.get("type")
    if p_type == "title":
        titles = p.get("title", [])
        return "".join(t.get("plain_text", "") for t in titles).strip()
    elif p_type == "rich_text":
        texts = p.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in texts).strip()
    elif p_type == "select":
        s = p.get("select")
        return s.get("name", "").strip() if s else ""
    elif p_type == "status":
        s = p.get("status")
        return s.get("name", "").strip() if s else ""
    elif p_type == "url":
        return p.get("url") or ""
    elif p_type == "number":
        n = p.get("number")
        return str(n) if n is not None else ""
    elif p_type == "date":
        d = p.get("date")
        return d.get("start", "") if d else ""
    return ""

def query_pages(client: Client, db_id: str, query_filter: Optional[Dict[str, Any]] = None, max_results: int = 150) -> List[Dict[str, Any]]:
    schema = inspect_database_schema(client, db_id)
    ds_id = schema.get("data_source_id")

    results: List[Dict[str, Any]] = []
    has_more = True
    start_cursor = None

    while has_more and len(results) < max_results:
        kwargs: Dict[str, Any] = {}
        if query_filter:
            kwargs["filter"] = query_filter
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        if ds_id:
            try:
                res = client.data_sources.query(data_source_id=ds_id, **kwargs)
                batch = res.get("results", [])
                results.extend(batch)
                has_more = res.get("has_more", False)
                start_cursor = res.get("next_cursor")
                if not has_more or not start_cursor:
                    break
                continue
            except Exception:
                pass

        body: Dict[str, Any] = {}
        if query_filter:
            body["filter"] = query_filter
        if start_cursor:
            body["start_cursor"] = start_cursor
        try:
            res = client.request(path=f"databases/{db_id}/query", method="POST", body=body)
            batch = res.get("results", [])
            results.extend(batch)
            has_more = res.get("has_more", False)
            start_cursor = res.get("next_cursor")
            if not has_more or not start_cursor:
                break
        except Exception as e:
            if not results:
                raise e
            break

    return results

def fetch_discovered_leads(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    client = get_notion_client()
    db_id = get_discovery_db_id()
    schema = inspect_database_schema(client, db_id)

    query_filter = None
    if status_filter and status_filter.lower() != "all":
        status_prop = schema.get("status_prop")
        status_type = schema.get("status_type") or "select"
        if status_prop:
            query_filter = {
                "property": status_prop,
                status_type: {"equals": status_filter}
            }

    raw_pages = query_pages(client, db_id, query_filter=query_filter, max_results=200)

    leads = []
    for p in raw_pages:
        lead = {
            "id": p["id"],
            "company": _get_page_prop_text(p, schema["title_prop"]) or "Unknown",
            "role": _get_page_prop_text(p, schema["role_prop"]) or "Software Role",
            "location": _get_page_prop_text(p, schema["location_prop"]) or "-",
            "status": _get_page_prop_text(p, schema["status_prop"]) or "New",
            "score": _get_page_prop_text(p, schema["score_prop"]) or "-",
            "category": _get_page_prop_text(p, schema["category_prop"]) or "-",
            "url": _get_page_prop_text(p, schema["url_prop"]) or "",
            "notes": _get_page_prop_text(p, schema["notes_prop"]) or "",
            "date": _get_page_prop_text(p, schema["date_prop"]) or "",
            "source_type": "notion"
        }
        leads.append(lead)

    return leads

def update_lead_status(page_id: str, new_status: str) -> bool:
    client = get_notion_client()
    db_id = get_discovery_db_id()
    schema = inspect_database_schema(client, db_id)
    status_prop = schema.get("status_prop")
    status_type = schema.get("status_type") or "select"

    if not status_prop:
        return False

    client.pages.update(
        page_id=page_id,
        properties={
            status_prop: {status_type: {"name": new_status}}
        }
    )
    return True

def delete_lead(page_id: str) -> bool:
    client = get_notion_client()
    client.pages.update(page_id=page_id, archived=True)
    return True

def clean_dismissed_leads(progress_callback: Optional[Callable[[int, int], None]] = None) -> int:
    client = get_notion_client()
    db_id = get_discovery_db_id()
    schema = inspect_database_schema(client, db_id)
    status_prop = schema.get("status_prop")
    status_type = schema.get("status_type") or "select"

    if not status_prop:
        return 0

    query_filter = {
        "property": status_prop,
        status_type: {"equals": "Dismissed"}
    }

    pages = query_pages(client, db_id, query_filter=query_filter, max_results=300)
    total = len(pages)
    cleaned = 0

    for i, p in enumerate(pages):
        try:
            client.pages.update(page_id=p["id"], archived=True)
            cleaned += 1
        except Exception:
            pass
        if progress_callback:
            progress_callback(i + 1, total)

    return cleaned

# --- Active Applications Tracker Operations ---

def fetch_active_applications(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches job applications from the active Notion Job Tracker database."""
    client = get_notion_client()
    db_id = get_tracker_db_id()
    schema = inspect_database_schema(client, db_id)

    query_filter = None
    if status_filter and status_filter.lower() != "all":
        status_prop = schema.get("status_prop")
        status_type = schema.get("status_type") or "select"
        if status_prop:
            query_filter = {
                "property": status_prop,
                status_type: {"equals": status_filter}
            }

    raw_pages = query_pages(client, db_id, query_filter=query_filter, max_results=150)
    apps = []
    for p in raw_pages:
        props = p.get("properties", {})
        priority = (props.get("Priority", {}).get("select") or {}).get("name", "Medium")
        contact = "".join(t.get("plain_text", "") for t in props.get("Contact", {}).get("rich_text", [])).strip()
        next_followup = (props.get("Next follow-up", {}).get("date") or {}).get("start", "")

        app = {
            "id": p["id"],
            "company": _get_page_prop_text(p, schema["title_prop"]) or "Unknown",
            "role": _get_page_prop_text(p, schema["role_prop"]) or "Software Role",
            "location": _get_page_prop_text(p, schema["location_prop"]) or "-",
            "status": _get_page_prop_text(p, schema["status_prop"]) or "Applied",
            "url": _get_page_prop_text(p, schema["url_prop"]) or "",
            "notes": _get_page_prop_text(p, schema["notes_prop"]) or "",
            "date": _get_page_prop_text(p, schema["date_prop"]) or "",
            "priority": priority,
            "contact": contact,
            "next_followup": next_followup,
            "source_type": "tracker"
        }
        apps.append(app)
    return apps

def update_application_status(page_id: str, new_status: str) -> bool:
    """Updates the stage/status of an active job application in Notion."""
    client = get_notion_client()
    db_id = get_tracker_db_id()
    schema = inspect_database_schema(client, db_id)
    status_prop = schema.get("status_prop")
    status_type = schema.get("status_type") or "select"

    if not status_prop:
        return False

    client.pages.update(
        page_id=page_id,
        properties={
            status_prop: {status_type: {"name": new_status}}
        }
    )
    return True

def delete_application(page_id: str) -> bool:
    """Archives an application from the Job Tracker database to trash."""
    client = get_notion_client()
    client.pages.update(page_id=page_id, archived=True)
    return True

def promote_lead_to_application(lead: Dict[str, Any], initial_status: str = "Applied") -> bool:
    """Promotes an approved discovery lead into the Job Applications tracker database."""
    client = get_notion_client()
    tracker_db_id = get_tracker_db_id()
    schema = inspect_database_schema(client, tracker_db_id)

    from datetime import date
    today_str = date.today().isoformat()

    title_prop = schema.get("title_prop") or "Company 1"
    properties: Dict[str, Any] = {
        title_prop: {
            "title": [{"text": {"content": lead.get("company", "Company")[:100]}}]
        }
    }

    if schema.get("role_prop"):
        properties[schema["role_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("role", "Software Role")[:200]}}]
        }

    if schema.get("url_prop") and lead.get("url"):
        properties[schema["url_prop"]] = {"url": lead["url"]}

    if schema.get("status_prop"):
        st_type = schema.get("status_type") or "select"
        properties[schema["status_prop"]] = {st_type: {"name": initial_status}}

    if schema.get("location_prop") and lead.get("location"):
        properties[schema["location_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("location", "")[:100]}}]
        }

    if schema.get("date_prop"):
        properties[schema["date_prop"]] = {"date": {"start": today_str}}

    score_val = lead.get("score")
    priority = "High" if str(score_val).isdigit() and int(score_val) >= 8 else "Medium"
    properties["Priority"] = {"select": {"name": priority}}

    if schema.get("notes_prop") and lead.get("notes"):
        properties[schema["notes_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("notes", "")[:1800]}}]
        }

    client.pages.create(
        parent={"database_id": tracker_db_id},
        properties=properties
    )
    return True

# --- Search Profile Operations ---

def load_search_profile() -> Dict[str, Any]:
    """Reads profile.yaml from job_discovery_inbox."""
    profile_path = os.path.join(DEFAULT_SCOUT_DIR, "profile.yaml")
    if not os.path.exists(profile_path):
        return {}
    try:
        import yaml
        with open(profile_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def save_search_profile(profile_data: Dict[str, Any]) -> bool:
    """Saves updated configuration to profile.yaml."""
    profile_path = os.path.join(DEFAULT_SCOUT_DIR, "profile.yaml")
    try:
        import yaml
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(profile_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        return True
    except Exception:
        return False

# --- Local Discovered Jobs & Notion Push Operations ---

def load_local_discovered_jobs() -> List[Dict[str, Any]]:
    """Loads latest discovered jobs from job_discovery_inbox/discovered_jobs.json."""
    json_path = os.path.join(DEFAULT_SCOUT_DIR, "discovered_jobs.json")
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                jobs = []
                for idx, item in enumerate(data):
                    jobs.append({
                        "id": f"local_{idx}",
                        "company": item.get("company", "Company"),
                        "role": item.get("role", "Software Role"),
                        "location": item.get("location", "Remote"),
                        "status": "New",
                        "score": str(item.get("score", "-")),
                        "category": item.get("category", "Search"),
                        "url": item.get("url", ""),
                        "notes": item.get("snippet", ""),
                        "date": "",
                        "source_type": "local",
                        "pushed": False
                    })
                return jobs
    except Exception:
        pass
    return []

def push_single_lead_to_notion(lead: Dict[str, Any]) -> bool:
    """Pushes a single local job lead to the Notion Discovery Inbox database."""
    client = get_notion_client()
    db_id = get_discovery_db_id()
    schema = inspect_database_schema(client, db_id)

    title_prop = schema.get("title_prop") or "Company"
    properties: Dict[str, Any] = {
        title_prop: {
            "title": [{"text": {"content": lead.get("company", "Company")[:100]}}]
        }
    }

    if schema.get("role_prop"):
        properties[schema["role_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("role", "Role")[:200]}}]
        }

    if schema.get("url_prop") and lead.get("url"):
        properties[schema["url_prop"]] = {"url": lead["url"]}

    if schema.get("status_prop"):
        st_type = schema.get("status_type") or "select"
        st_val = lead.get("status", "New")
        properties[schema["status_prop"]] = {st_type: {"name": st_val}}

    if schema.get("location_prop") and lead.get("location"):
        properties[schema["location_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("location", "")[:100]}}]
        }

    if schema.get("score_prop") and lead.get("score"):
        try:
            properties[schema["score_prop"]] = {"number": int(lead["score"])}
        except (ValueError, TypeError):
            pass

    if schema.get("notes_prop") and lead.get("notes"):
        properties[schema["notes_prop"]] = {
            "rich_text": [{"text": {"content": lead.get("notes", "")[:1800]}}]
        }

    # Deduplication check by URL
    if lead.get("url") and schema.get("url_prop"):
        dup_filter = {
            "property": schema["url_prop"],
            "url": {"equals": lead["url"]}
        }
        dups = query_pages(client, db_id, query_filter=dup_filter, max_results=1)
        if dups:
            # Already exists in Notion
            return False

    client.pages.create(
        parent={"database_id": db_id},
        properties=properties
    )
    return True

def push_leads_to_notion(leads: List[Dict[str, Any]], progress_callback: Optional[Callable[[int, int], None]] = None) -> int:
    """Pushes a list of local leads to Notion, removing successfully pushed items from local pending inbox."""
    success_count = 0
    total = len(leads)
    pushed_urls = set()

    for idx, lead in enumerate(leads):
        try:
            ok = push_single_lead_to_notion(lead)
            if ok:
                success_count += 1
                lead["pushed"] = True
                if lead.get("url"):
                    pushed_urls.add(lead["url"])
        except Exception:
            pass
        if progress_callback:
            progress_callback(idx + 1, total)

    # Sync pushed leads with local files
    if pushed_urls:
        seen_path = os.path.join(DEFAULT_SCOUT_DIR, "seen_jobs.json")
        try:
            seen_set = set()
            if os.path.exists(seen_path):
                with open(seen_path, "r", encoding="utf-8") as f:
                    seen_set = set(json.load(f))
            seen_set.update(pushed_urls)
            with open(seen_path, "w", encoding="utf-8") as f:
                json.dump(list(seen_set), f, indent=2)
        except Exception:
            pass

        disc_path = os.path.join(DEFAULT_SCOUT_DIR, "discovered_jobs.json")
        try:
            if os.path.exists(disc_path):
                with open(disc_path, "r", encoding="utf-8") as f:
                    disc_list = json.load(f)
                remaining = [j for j in disc_list if j.get("url") not in pushed_urls]
                with open(disc_path, "w", encoding="utf-8") as f:
                    json.dump(remaining, f, indent=2)
        except Exception:
            pass

    return success_count

# --- Scout Process Control ---

def stop_scout_process() -> bool:
    """Instantly kills the running scout subprocess and its process group."""
    global _ACTIVE_SCOUT_PROC
    with _SCOUT_LOCK:
        if _ACTIVE_SCOUT_PROC and _ACTIVE_SCOUT_PROC.poll() is None:
            try:
                pgid = os.getpgid(_ACTIVE_SCOUT_PROC.pid)
                os.killpg(pgid, signal.SIGTERM)
                threading.Event().wait(0.2)
                if _ACTIVE_SCOUT_PROC.poll() is None:
                    os.killpg(pgid, signal.SIGKILL)
                return True
            except Exception:
                try:
                    _ACTIVE_SCOUT_PROC.kill()
                    return True
                except Exception:
                    pass
    return False

def run_scout_process(
    freshness: str = "24h",
    category: str = "all",
    max_queries: int = 25,
    rescan: bool = False,
    log_callback: Optional[Callable[[str], None]] = None
) -> int:
    """Runs scout.py locally (without automatic pushing to Notion)."""
    global _ACTIVE_SCOUT_PROC
    scout_dir = DEFAULT_SCOUT_DIR
    python_bin = os.path.join(scout_dir, ".venv/bin/python")
    if not os.path.exists(python_bin):
        python_bin = sys.executable

    scout_script = os.path.join(scout_dir, "scout.py")
    if not os.path.exists(scout_script):
        if log_callback:
            log_callback(f"❌ scout.py not found at: {scout_script}\n")
            log_callback("💡 To run the automated job scraper, clone job-discovery-inbox alongside this project:\n")
            log_callback("   git clone https://github.com/AhmedKhalifa3/job-discovery-inbox.git\n")
            log_callback("   or set SCOUT_PROJECT_PATH in your .env file.\n\n")
        return 1

    # NOTE: Does NOT pass --push-notion so user reviews matches before pushing!
    cmd = [
        python_bin,
        "-u",  # Unbuffered output for instant real-time log streaming
        scout_script,
        "--fresh", freshness,
        "--category", category,
        "--max-queries", str(max_queries)
    ]
    if rescan:
        cmd.append("--rescan")

    if log_callback:
        log_callback(f"🚀 Running scout (Local Search Mode):\n   {' '.join(cmd)}\n\n")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        cmd,
        cwd=scout_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
        start_new_session=True  # Separate process group for instant killpg
    )

    with _SCOUT_LOCK:
        _ACTIVE_SCOUT_PROC = process

    try:
        for line in iter(process.stdout.readline, ''):
            if log_callback:
                log_callback(line)
    except Exception:
        pass
    finally:
        if process.stdout:
            process.stdout.close()

    ret = process.wait()

    with _SCOUT_LOCK:
        _ACTIVE_SCOUT_PROC = None

    if ret in (-signal.SIGTERM, -signal.SIGKILL, 137):
        if log_callback:
            log_callback("\n⏹️ Scout process stopped immediately by user.\n")
        return -1

    if log_callback:
        log_callback(f"\n✨ Scout completed (exit code {ret}). Review findings above and push to Notion when ready!\n")
    return ret
