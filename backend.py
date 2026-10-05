"""
Backend controller for Career Dashboard GUI.
Handles Notion API operations and Scout subprocess execution.
"""

import os
import sys
import subprocess
import threading
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables (checking local, then peer project folders)
load_dotenv()
if not os.getenv("NOTION_API_KEY"):
    for peer_env in ["../notion-tracker-mcp/.env", "../job_discovery_inbox/.env"]:
        if os.path.exists(peer_env):
            load_dotenv(peer_env)
            break

def clean_id(raw_id: str) -> str:
    if not raw_id:
        return ""
    return raw_id.split("?")[0].rstrip("/").split("/")[-1].replace("-", "")

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DISCOVERED_JOBS_DB_ID = clean_id(os.getenv("NOTION_DISCOVERED_JOBS_DB_ID", ""))
NOTION_JOB_TRACKER_DB_ID = clean_id(os.getenv("NOTION_JOB_TRACKER_DB_ID", ""))

# Path to job_discovery_inbox
DEFAULT_SCOUT_DIR = os.path.abspath(
    os.getenv("SCOUT_PROJECT_PATH", os.path.join(os.path.dirname(__file__), "../job_discovery_inbox"))
)

_SCHEMA_CACHE: Dict[str, Any] = {}

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

def run_scout_process(
    freshness: str = "24h",
    category: str = "all",
    log_callback: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None
) -> int:
    scout_dir = DEFAULT_SCOUT_DIR
    python_bin = os.path.join(scout_dir, ".venv/bin/python")
    if not os.path.exists(python_bin):
        python_bin = sys.executable

    scout_script = os.path.join(scout_dir, "scout.py")
    if not os.path.exists(scout_script):
        if log_callback:
            log_callback(f"❌ scout.py not found at {scout_script}\n")
        return 1

    cmd = [python_bin, scout_script, "--fresh", freshness, "--category", category, "--push-notion"]
    if log_callback:
        log_callback(f"🚀 Running command: {' '.join(cmd)}\n")

    process = subprocess.Popen(
        cmd,
        cwd=scout_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    while True:
        if stop_event and stop_event.is_set():
            process.terminate()
            if log_callback:
                log_callback("⏹️ Scout process stopped by user.\n")
            return -1

        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line and log_callback:
            log_callback(line)

    ret = process.poll() or 0
    if log_callback:
        log_callback(f"\n✨ Scout completed with exit code {ret}.\n")
    return ret
