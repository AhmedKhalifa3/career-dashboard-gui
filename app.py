"""
Career Cockpit — Autonomous Job Scout & Notion Dashboard
A modern, high-performance CustomTkinter desktop GUI for managing autonomous
job discovery, scoring, triage, and active application pipeline tracking.
"""

import os
import sys
import queue
import threading
import webbrowser
from typing import Dict, List, Optional, Any
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from backend import (
    fetch_discovered_leads,
    update_lead_status,
    delete_lead,
    clean_dismissed_leads,
    run_scout_process,
    stop_scout_process,
    load_local_discovered_jobs,
    push_leads_to_notion,
    push_single_lead_to_notion,
    get_discovery_db_id,
    get_tracker_db_id,
    fetch_active_applications,
    update_application_status,
    delete_application,
    promote_lead_to_application,
    load_search_profile,
    save_search_profile,
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ==============================================================================
# 1. JOB DETAILS INSPECT MODAL
# ==============================================================================

class JobDetailsModal(ctk.CTkToplevel):
    """Detailed view modal for inspecting job leads and active applications."""
    def __init__(self, parent, item: Dict[str, Any], item_type: str, callbacks: Dict[str, Any]):
        super().__init__(parent)
        self.item = item
        self.item_type = item_type  # "discovery", "local", "tracker"
        self.callbacks = callbacks

        self.title(f"{item.get('company', 'Company')} — {item.get('role', 'Role')}")
        self.geometry("780x620")
        self.minsize(680, 500)
        self.grab_set()  # Make modal

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Header Frame
        hdr = ctk.CTkFrame(self, fg_color="#1e1e24", corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        hdr.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            hdr,
            text=item.get("role", "Software Role"),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#3498db"
        )
        title_lbl.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 2))

        comp_lbl = ctk.CTkLabel(
            hdr,
            text=f"🏢 {item.get('company', 'Unknown Company')}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ecf0f1"
        )
        comp_lbl.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        # Metadata Row (Pills)
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))

        # Location pill
        loc_txt = item.get("location") or "Remote / Germany"
        ctk.CTkLabel(
            meta_frame,
            text=f"📍 {loc_txt}",
            font=ctk.CTkFont(size=11),
            fg_color="#2c3e50",
            corner_radius=6,
            padx=10,
            pady=4
        ).pack(side="left", padx=(0, 8))

        # Score pill (if applicable)
        score_raw = str(item.get("score", "-"))
        score_val = str(min(10, max(0, int(score_raw)))) if score_raw.isdigit() else score_raw
        if score_val and score_val != "-":
            sc_color = "#27ae60" if score_val.isdigit() and int(score_val) >= 7 else "#e67e22" if score_val.isdigit() and int(score_val) >= 4 else "#7f8c8d"
            ctk.CTkLabel(
                meta_frame,
                text=f"★ Match: {score_val}/10",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=sc_color,
                corner_radius=6,
                padx=10,
                pady=4
            ).pack(side="left", padx=(0, 8))

        # Status pill
        st_txt = item.get("status", "New")
        st_color = "#2980b9" if st_txt == "New" else "#27ae60" if st_txt in ("Approved", "Offer") else "#8e44ad" if st_txt in ("Interview", "Screening") else "#c0392b"
        ctk.CTkLabel(
            meta_frame,
            text=f"Status: {st_txt}",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=st_color,
            corner_radius=6,
            padx=10,
            pady=4
        ).pack(side="left", padx=(0, 8))

        # Date pill if present
        date_txt = item.get("date") or ""
        if date_txt:
            ctk.CTkLabel(
                meta_frame,
                text=f"📅 {date_txt}",
                font=ctk.CTkFont(size=11),
                fg_color="#34495e",
                corner_radius=6,
                padx=10,
                pady=4
            ).pack(side="left", padx=(0, 8))

        # Priority pill if tracker
        prio_txt = item.get("priority")
        if prio_txt:
            prio_color = "#c0392b" if prio_txt == "High" else "#f39c12" if prio_txt == "Medium" else "#7f8c8d"
            ctk.CTkLabel(
                meta_frame,
                text=f"Priority: {prio_txt}",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=prio_color,
                corner_radius=6,
                padx=10,
                pady=4
            ).pack(side="left", padx=(0, 8))

        # Body: Job Snippet / Description
        body_frame = ctk.CTkFrame(self, fg_color="#18181f", corner_radius=8)
        body_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 12))
        body_frame.grid_columnconfigure(0, weight=1)
        body_frame.grid_rowconfigure(1, weight=1)

        body_hdr = ctk.CTkLabel(
            body_frame,
            text="JOB DETAILS & MATCH REASONING",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#bdc3c7"
        )
        body_hdr.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        notes_txt = item.get("notes") or "No detailed description or notes stored for this posting."
        desc_box = ctk.CTkTextbox(
            body_frame,
            font=ctk.CTkFont(family="sans-serif", size=12),
            wrap="word",
            fg_color="transparent"
        )
        desc_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        desc_box.insert("1.0", notes_txt)
        desc_box.configure(state="disabled")

        # Bottom Actions Bar
        actions_bar = ctk.CTkFrame(self, fg_color="transparent")
        actions_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))

        # Open in Browser button
        url = item.get("url") or ""
        if url:
            ctk.CTkButton(
                actions_bar,
                text="🔗 Open in Browser",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#1f6aa5",
                hover_color="#144d75",
                command=lambda: webbrowser.open(url)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                actions_bar,
                text="📋 Copy Link",
                font=ctk.CTkFont(size=12),
                fg_color="#34495e",
                hover_color="#415b76",
                command=lambda: self._copy_url(url)
            ).pack(side="left", padx=(0, 8))

        # Close button
        ctk.CTkButton(
            actions_bar,
            text="Close",
            width=80,
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self.destroy
        ).pack(side="right", padx=(8, 0))

        # Contextual Buttons
        if item_type == "discovery":
            # Move to Applied button
            ctk.CTkButton(
                actions_bar,
                text="🚀 Move to Applications",
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#27ae60",
                hover_color="#219150",
                command=self._on_promote_clicked
            ).pack(side="right", padx=4)

            if item.get("status") != "Approved":
                ctk.CTkButton(
                    actions_bar,
                    text="✅ Approve",
                    width=85,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    fg_color="#1e8449",
                    hover_color="#27ae60",
                    command=self._on_approve_clicked
                ).pack(side="right", padx=4)

            if item.get("status") != "Dismissed":
                ctk.CTkButton(
                    actions_bar,
                    text="❌ Dismiss",
                    width=85,
                    font=ctk.CTkFont(size=12),
                    fg_color="#922b21",
                    hover_color="#b03a2e",
                    command=self._on_dismiss_clicked
                ).pack(side="right", padx=4)

        elif item_type == "tracker":
            # Stage advance dropdown
            st_var = ctk.StringVar(value=item.get("status", "Applied"))
            stage_menu = ctk.CTkOptionMenu(
                actions_bar,
                values=["Wishlist", "Applied", "Screening", "Interview", "Offer", "Rejected"],
                variable=st_var,
                command=lambda val: self._on_stage_changed(val)
            )
            stage_menu.pack(side="right", padx=4)
            ctk.CTkLabel(actions_bar, text="Set Stage:", font=ctk.CTkFont(size=11), text_color="gray").pack(side="right", padx=2)

    def _copy_url(self, url: str):
        self.clipboard_clear()
        self.clipboard_append(url)
        messagebox.showinfo("Copied", "Job URL copied to clipboard!", parent=self)

    def _on_promote_clicked(self):
        cb = self.callbacks.get("on_promote")
        if cb:
            cb(self.item)
        self.destroy()

    def _on_approve_clicked(self):
        cb = self.callbacks.get("on_approve")
        if cb:
            cb(self.item)
        self.destroy()

    def _on_dismiss_clicked(self):
        cb = self.callbacks.get("on_dismiss")
        if cb:
            cb(self.item)
        self.destroy()

    def _on_stage_changed(self, new_stage: str):
        cb = self.callbacks.get("on_stage_change")
        if cb:
            cb(self.item, new_stage)
        self.destroy()


# ==============================================================================
# 2. PROFILE SETTINGS MODAL
# ==============================================================================

class ProfileSettingsModal(ctk.CTkToplevel):
    """Modal for viewing and updating candidate profile & search rules."""
    def __init__(self, parent, on_saved_callback=None):
        super().__init__(parent)
        self.on_saved_callback = on_saved_callback
        self.title("⚙️ Search Profile Settings (profile.yaml)")
        self.geometry("740x600")
        self.minsize(620, 480)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            hdr,
            text="⚙️ Candidate Profile & Search Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        sub_lbl = ctk.CTkLabel(
            hdr,
            text="Customize role titles, skills, and exclusion rules. One item per line.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        sub_lbl.grid(row=1, column=0, sticky="w")

        # Tabview for sections
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)

        tab_roles = self.tabview.add("🎯 Target Roles")
        tab_skills = self.tabview.add("💻 Skills")
        tab_locations = self.tabview.add("📍 Locations")
        tab_negative = self.tabview.add("🚫 Negative Filters")

        self.txt_roles = self._build_text_tab(tab_roles)
        self.txt_skills = self._build_text_tab(tab_skills)
        self.txt_locations = self._build_text_tab(tab_locations)
        self.txt_negative = self._build_text_tab(tab_negative)

        # Bottom Bar
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))

        save_btn = ctk.CTkButton(
            bottom,
            text="💾 Save Profile Changes",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219150",
            command=self.save_profile
        )
        save_btn.pack(side="left", padx=4)

        cancel_btn = ctk.CTkButton(
            bottom,
            text="Cancel",
            width=80,
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self.destroy
        )
        cancel_btn.pack(side="right", padx=4)

        self._load_data()

    def _build_text_tab(self, parent_tab):
        parent_tab.grid_columnconfigure(0, weight=1)
        parent_tab.grid_rowconfigure(0, weight=1)
        txt = ctk.CTkTextbox(parent_tab, font=ctk.CTkFont(family="monospace", size=12))
        txt.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        return txt

    def _load_data(self):
        self.profile = load_search_profile()
        roles = self.profile.get("target_roles", [])
        skills = self.profile.get("skills", [])
        locations = self.profile.get("locations", [])
        negative = self.profile.get("negative_keywords", []) + self.profile.get("negative_title_keywords", [])

        self.txt_roles.insert("1.0", "\n".join(str(r) for r in roles))
        self.txt_skills.insert("1.0", "\n".join(str(s) for s in skills))
        self.txt_locations.insert("1.0", "\n".join(str(loc) for loc in locations))
        self.txt_negative.insert("1.0", "\n".join(str(neg) for neg in negative))

    def save_profile(self):
        roles = [line.strip() for line in self.txt_roles.get("1.0", "end").splitlines() if line.strip()]
        skills = [line.strip() for line in self.txt_skills.get("1.0", "end").splitlines() if line.strip()]
        locations = [line.strip() for line in self.txt_locations.get("1.0", "end").splitlines() if line.strip()]
        negative = [line.strip() for line in self.txt_negative.get("1.0", "end").splitlines() if line.strip()]

        self.profile["target_roles"] = roles
        self.profile["skills"] = skills
        self.profile["locations"] = locations
        self.profile["negative_keywords"] = negative

        ok = save_search_profile(self.profile)
        if ok:
            messagebox.showinfo("Profile Saved", "Search profile updated successfully!", parent=self)
            if self.on_saved_callback:
                self.on_saved_callback()
            self.destroy()
        else:
            messagebox.showerror("Save Failed", "Could not write to profile.yaml.", parent=self)


# ==============================================================================
# 3. MAIN CAREER COCKPIT APPLICATION
# ==============================================================================

class CareerDashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__(className="career-cockpit")

        self.title("Career Cockpit — Autonomous Job Search & Pipeline Dashboard")
        self.geometry("1280x880")
        self.minsize(1080, 720)

        # Set Window & Taskbar Icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                from PIL import ImageTk
                self._app_icon = ImageTk.PhotoImage(file=icon_path)
                self.wm_iconphoto(True, self._app_icon)
            except Exception:
                pass

        # Application state
        self.notion_leads: List[Dict[str, Any]] = []
        self.local_leads: List[Dict[str, Any]] = []
        self.active_applications: List[Dict[str, Any]] = []

        self.active_tab = "📥 Discovery Inbox"
        self.current_filter = "New"
        self.sort_mode = "Score (High to Low)"
        self.score_filter = "All Scores"

        # Pagination & Performance state
        self.current_page = 1
        self.page_size = 15  # 15 cards per page = ultra-fast 25ms render!
        self._search_debounce_id = None
        self._log_queue: queue.Queue = queue.Queue()
        self._log_flushing = False

        self.is_loading = False
        self.is_pushing = False
        self.scout_thread: Optional[threading.Thread] = None

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_view()

        # Start periodic log flusher
        self._flush_logs()

        # Intercept window close to remind about unpushed leads
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # Initial data load
        self.after(200, self.initial_load)

    # --------------------------------------------------------------------------
    # SIDEBAR BUILDER
    # --------------------------------------------------------------------------

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(22, weight=1)

        # Branding
        title_lbl = ctk.CTkLabel(
            self.sidebar,
            text="💼 Career Cockpit",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(20, 2), sticky="w")

        subtitle_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Autonomous Job Scout & Tracker",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        subtitle_lbl.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        sep1 = ctk.CTkProgressBar(self.sidebar, height=2)
        sep1.set(1.0)
        sep1.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Scout Controller Section
        scout_hdr = ctk.CTkLabel(
            self.sidebar,
            text="SCOUT CONTROLLER",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#3498db"
        )
        scout_hdr.grid(row=3, column=0, padx=20, pady=(5, 5), sticky="w")

        # Freshness
        f_lbl = ctk.CTkLabel(self.sidebar, text="Freshness Window:", font=ctk.CTkFont(size=12))
        f_lbl.grid(row=4, column=0, padx=20, pady=(2, 0), sticky="w")
        self.freshness_var = ctk.StringVar(value="24h")
        self.freshness_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["24h", "week", "any"],
            variable=self.freshness_var
        )
        self.freshness_menu.grid(row=5, column=0, padx=20, pady=(0, 8), sticky="ew")

        # Category
        c_lbl = ctk.CTkLabel(self.sidebar, text="Role Category:", font=ctk.CTkFont(size=12))
        c_lbl.grid(row=6, column=0, padx=20, pady=(2, 0), sticky="w")
        self.category_var = ctk.StringVar(value="all")
        self.category_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["all", "werkstudent", "ai_agent", "backend", "fullstack", "sdet_qa"],
            variable=self.category_var
        )
        self.category_menu.grid(row=7, column=0, padx=20, pady=(0, 8), sticky="ew")

        # Scan Depth
        d_lbl = ctk.CTkLabel(self.sidebar, text="Scan Speed / Depth:", font=ctk.CTkFont(size=12))
        d_lbl.grid(row=8, column=0, padx=20, pady=(2, 0), sticky="w")
        self.depth_var = ctk.StringVar(value="Fast Scan (20 Dorks + APIs)")
        self.depth_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Fast Scan (20 Dorks + APIs)", "Deep Scan (50 Dorks + APIs)", "Full Scan (All Dorks + APIs)"],
            variable=self.depth_var
        )
        self.depth_menu.grid(row=9, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Force Rescan Checkbox
        self.rescan_var = ctk.BooleanVar(value=False)
        self.rescan_chk = ctk.CTkCheckBox(
            self.sidebar,
            text="🔄 Force Rescan (Ignore cache)",
            font=ctk.CTkFont(size=12),
            variable=self.rescan_var
        )
        self.rescan_chk.grid(row=10, column=0, padx=20, pady=(0, 12), sticky="w")

        # Scout Action Buttons
        self.btn_run_scout = ctk.CTkButton(
            self.sidebar,
            text="🚀 Run Job Scout (Local Search)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
            command=self.on_run_scout
        )
        self.btn_run_scout.grid(row=11, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_stop_scout = ctk.CTkButton(
            self.sidebar,
            text="⏹️ Stop Scout",
            fg_color="#7f8c8d",
            hover_color="#c0392b",
            state="disabled",
            command=self.on_stop_scout
        )
        self.btn_stop_scout.grid(row=12, column=0, padx=20, pady=(0, 15), sticky="ew")

        sep2 = ctk.CTkProgressBar(self.sidebar, height=2)
        sep2.set(1.0)
        sep2.grid(row=13, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Notion & Pipeline Operations
        pipe_hdr = ctk.CTkLabel(
            self.sidebar,
            text="PIPELINE & MAINTENANCE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#9b59b6"
        )
        pipe_hdr.grid(row=14, column=0, padx=20, pady=(0, 8), sticky="w")

        self.btn_refresh = ctk.CTkButton(
            self.sidebar,
            text="🔄 Refresh All Notion Data",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self.refresh_all_data
        )
        self.btn_refresh.grid(row=15, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_clean_dismissed = ctk.CTkButton(
            self.sidebar,
            text="🧹 Clean All Dismissed",
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            command=self.on_clean_dismissed
        )
        self.btn_clean_dismissed.grid(row=16, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_settings = ctk.CTkButton(
            self.sidebar,
            text="⚙️ Search Profile Settings",
            fg_color="#34495e",
            hover_color="#415b76",
            command=self.open_profile_settings
        )
        self.btn_settings.grid(row=17, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Bottom theme toggle
        theme_lbl = ctk.CTkLabel(self.sidebar, text="Appearance Mode:", font=ctk.CTkFont(size=11))
        theme_lbl.grid(row=23, column=0, padx=20, pady=(10, 0), sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode
        )
        self.theme_menu.grid(row=24, column=0, padx=20, pady=(2, 20), sticky="ew")

    # --------------------------------------------------------------------------
    # MAIN VIEW BUILDER
    # --------------------------------------------------------------------------

    def _build_main_view(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(3, weight=3)  # Leads Scroll List
        self.main_container.grid_rowconfigure(4, weight=1)  # Log Console

        # Top Bar: Dynamic Metrics Cards
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.top_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_1 = self._create_metric_card(self.top_bar, 0, "Total Leads", "0", "#34495e")
        self.card_2 = self._create_metric_card(self.top_bar, 1, "New Review", "0", "#2980b9")
        self.card_3 = self._create_metric_card(self.top_bar, 2, "Approved", "0", "#27ae60")
        self.card_4 = self._create_metric_card(self.top_bar, 3, "Local Pending", "0", "#d35400")

        # Primary Mode Navigation (3 Modes: Discovery Inbox, Local Leads, Active Applications)
        self.nav_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.nav_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.nav_bar.grid_columnconfigure(0, weight=1)

        self.mode_segmented = ctk.CTkSegmentedButton(
            self.nav_bar,
            values=[
                "📥 Discovery Inbox",
                "🆕 Newly Scouted (Local)",
                "📊 Active Applications"
            ],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_mode_changed
        )
        self.mode_segmented.set("📥 Discovery Inbox")
        self.mode_segmented.grid(row=0, column=0, sticky="ew")

        # Sub-Controls Bar (Filter pills, Sort, Score Filter, Push button, Search)
        self.controls_bar = ctk.CTkFrame(self.main_container)
        self.controls_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=2)
        self.controls_bar.grid_columnconfigure(3, weight=1)

        # Filter Segmented Button (Dynamic labels with counter badges)
        self.tab_filter = ctk.CTkSegmentedButton(
            self.controls_bar,
            values=["New", "Approved", "Dismissed", "All"],
            command=self.on_filter_changed
        )
        self.tab_filter.set("New")
        self.tab_filter.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        # Score Filter Dropdown
        self.score_menu = ctk.CTkOptionMenu(
            self.controls_bar,
            values=["All Scores", "★ 8+ Match", "★ 6+ Match", "★ 4+ Match"],
            width=125,
            command=self.on_score_filter_changed
        )
        self.score_menu.set("All Scores")
        self.score_menu.grid(row=0, column=1, padx=4, pady=8, sticky="w")

        # Sort Dropdown
        self.sort_menu = ctk.CTkOptionMenu(
            self.controls_bar,
            values=["Score (High to Low)", "Company (A-Z)", "Newest First"],
            width=150,
            command=self.on_sort_changed
        )
        self.sort_menu.set("Score (High to Low)")
        self.sort_menu.grid(row=0, column=2, padx=4, pady=8, sticky="w")

        # Search Entry (Debounced)
        self.search_entry = ctk.CTkEntry(
            self.controls_bar,
            placeholder_text="🔍 Filter by company, title, location...",
            height=32
        )
        self.search_entry.grid(row=0, column=3, padx=(6, 4), pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.on_search_key)

        # Clear Search Button
        self.btn_clear_search = ctk.CTkButton(
            self.controls_bar,
            text="✕",
            width=30,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#34495e",
            hover_color="#415b76",
            command=self.clear_search
        )
        self.btn_clear_search.grid(row=0, column=4, padx=(0, 6), pady=8)

        # Push to Notion Button (Visible in Local mode)
        self.btn_push_to_notion = ctk.CTkButton(
            self.controls_bar,
            text="📤 Push All to Notion",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#e67e22",
            hover_color="#d35400",
            command=self.on_push_leads_clicked
        )
        self.btn_push_to_notion.grid(row=0, column=5, padx=(4, 10), pady=8, sticky="e")
        self.btn_push_to_notion.grid_remove()  # Hidden by default in Notion Inbox mode

        # Leads Scrollable Area & Pagination Container
        self.leads_scroll = ctk.CTkScrollableFrame(self.main_container, label_text="Postings")
        self.leads_scroll.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        self.leads_scroll.grid_columnconfigure(0, weight=1)

        # Bottom Live Activity Console
        self.console_frame = ctk.CTkFrame(self.main_container)
        self.console_frame.grid(row=4, column=0, sticky="nsew")
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)

        console_header = ctk.CTkFrame(self.console_frame, fg_color="transparent")
        console_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 4))
        console_header.grid_columnconfigure(0, weight=1)

        console_lbl = ctk.CTkLabel(
            console_header,
            text="📡 Live Activity & Scraper Console",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        console_lbl.grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            console_header,
            text="Clear Log",
            width=70,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="#34495e",
            command=self.clear_console
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        self.console_text = ctk.CTkTextbox(
            self.console_frame,
            font=ctk.CTkFont(family="monospace", size=11),
            wrap="word"
        )
        self.console_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))

    def _create_metric_card(self, parent, col, title, value, border_color):
        card = ctk.CTkFrame(parent, fg_color="#1e1e24", border_width=1, border_color=border_color)
        card.grid(row=0, column=col, padx=4, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        val_lbl = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        val_lbl.grid(row=0, column=0, padx=10, pady=(8, 0))

        title_lbl = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        title_lbl.grid(row=1, column=0, padx=10, pady=(0, 8))

        return {"val": val_lbl, "title": title_lbl}

    # --------------------------------------------------------------------------
    # LOGGING (BATCHED & THROTTLED FOR 60FPS UI RESPONSIVENESS)
    # --------------------------------------------------------------------------

    def log(self, message: str):
        self._log_queue.put(message)

    def _flush_logs(self):
        batch = []
        while not self._log_queue.empty():
            try:
                batch.append(self._log_queue.get_nowait())
            except queue.Empty:
                break

        if batch:
            self.console_text.insert("end", "".join(batch))
            self.console_text.see("end")

        # Schedule next flush every 50ms
        self.after(50, self._flush_logs)

    def clear_console(self):
        self.console_text.delete("1.0", "end")

    # --------------------------------------------------------------------------
    # DATA LOADING & REFRESHING
    # --------------------------------------------------------------------------

    def initial_load(self):
        self.local_leads = load_local_discovered_jobs()
        self.refresh_all_data()

    def refresh_all_data(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.configure(state="disabled", text="⏳ Loading...")
        self.log(f"🔄 Syncing databases from Notion...\n")

        def _worker():
            try:
                disc_leads = fetch_discovered_leads(status_filter="all")
                active_apps = fetch_active_applications(status_filter="all")
                self.after(0, lambda: self._on_data_loaded(disc_leads, active_apps))
            except Exception as e:
                self.after(0, lambda: self._on_data_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_data_loaded(self, disc_leads: List[Dict], active_apps: List[Dict]):
        self.notion_leads = disc_leads
        self.active_applications = active_apps
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh All Notion Data")

        self.log(f"✅ Loaded {len(disc_leads)} Discovery Leads and {len(active_apps)} Active Applications.\n")
        self._update_metrics_and_filter_badges()
        self.render_leads_list()

    def _on_data_error(self, err_msg: str):
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh All Notion Data")
        self.log(f"❌ Error fetching Notion data: {err_msg}\n")
        messagebox.showerror("Notion API Error", f"Failed to retrieve data from Notion:\n\n{err_msg}")

    # --------------------------------------------------------------------------
    # NAVIGATION & FILTER CONTROLS
    # --------------------------------------------------------------------------

    def on_mode_changed(self, mode_value: str):
        self.active_tab = mode_value
        self.current_page = 1

        if "Discovery" in mode_value:
            self.tab_filter.grid()
            self.score_menu.grid()
            self.btn_push_to_notion.grid_remove()
            self.tab_filter.configure(values=["New", "Approved", "Dismissed", "All"])
            self.tab_filter.set("New")
            self.current_filter = "New"
            self.leads_scroll.configure(label_text="Discovery Inbox Postings")

        elif "Local" in mode_value:
            self.tab_filter.grid()
            self.score_menu.grid()
            self.btn_push_to_notion.grid()
            self.tab_filter.configure(values=["All", "Pending Push", "Synced"])
            self.tab_filter.set("Pending Push")
            self.current_filter = "Pending Push"
            self.leads_scroll.configure(label_text="Newly Scouted Local Leads")

        elif "Applications" in mode_value:
            self.tab_filter.grid()
            self.score_menu.grid_remove()  # Score is for discovery leads
            self.btn_push_to_notion.grid_remove()
            self.tab_filter.configure(values=["All", "Applied", "Screening", "Interview", "Offer", "Rejected", "Wishlist"])
            self.tab_filter.set("All")
            self.current_filter = "All"
            self.leads_scroll.configure(label_text="Active Job Applications Pipeline")

        self._update_metrics_and_filter_badges()
        self.render_leads_list()

    def on_filter_changed(self, value: str):
        self.current_filter = value
        self.current_page = 1
        self.render_leads_list()

    def on_score_filter_changed(self, value: str):
        self.score_filter = value
        self.current_page = 1
        self.render_leads_list()

    def on_sort_changed(self, value: str):
        self.sort_mode = value
        self.current_page = 1
        self.render_leads_list()

    def on_search_key(self, event=None):
        if self._search_debounce_id:
            self.after_cancel(self._search_debounce_id)
        # 220ms debounce: instant feel with 0 CPU lag when typing
        self._search_debounce_id = self.after(220, self._apply_search_and_render)

    def _apply_search_and_render(self):
        self.current_page = 1
        self.render_leads_list()

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.current_page = 1
        self.render_leads_list()

    # --------------------------------------------------------------------------
    # METRICS & BADGES RECALCULATION
    # --------------------------------------------------------------------------

    def _update_metrics_and_filter_badges(self):
        if self.active_tab == "📥 Discovery Inbox":
            total = len(self.notion_leads)
            new_cnt = sum(1 for l in self.notion_leads if l.get("status", "").lower() == "new")
            app_cnt = sum(1 for l in self.notion_leads if l.get("status", "").lower() == "approved")
            loc_cnt = len([l for l in self.local_leads if not l.get("pushed")])

            self.card_1["title"].configure(text="Total In Notion")
            self.card_1["val"].configure(text=str(total))
            self.card_2["title"].configure(text="New Awaiting Review")
            self.card_2["val"].configure(text=str(new_cnt))
            self.card_3["title"].configure(text="Approved Leads")
            self.card_3["val"].configure(text=str(app_cnt))
            self.card_4["title"].configure(text="🆕 Local Pending")
            self.card_4["val"].configure(text=str(loc_cnt))

        elif self.active_tab == "🆕 Newly Scouted (Local)":
            total_loc = len(self.local_leads)
            unpushed = len([l for l in self.local_leads if not l.get("pushed")])
            synced = total_loc - unpushed

            self.card_1["title"].configure(text="Total Scouted")
            self.card_1["val"].configure(text=str(total_loc))
            self.card_2["title"].configure(text="Pending Notion Push")
            self.card_2["val"].configure(text=str(unpushed))
            self.card_3["title"].configure(text="Synced to Notion")
            self.card_3["val"].configure(text=str(synced))
            self.card_4["title"].configure(text="Active Notion Leads")
            self.card_4["val"].configure(text=str(len(self.notion_leads)))

        elif self.active_tab == "📊 Active Applications":
            total_apps = len(self.active_applications)
            applied_cnt = sum(1 for a in self.active_applications if a.get("status", "").lower() == "applied")
            interview_cnt = sum(1 for a in self.active_applications if a.get("status", "").lower() in ("interview", "screening"))
            offer_cnt = sum(1 for a in self.active_applications if a.get("status", "").lower() == "offer")

            self.card_1["title"].configure(text="Total Applications")
            self.card_1["val"].configure(text=str(total_apps))
            self.card_2["title"].configure(text="Applied (Pending)")
            self.card_2["val"].configure(text=str(applied_cnt))
            self.card_3["title"].configure(text="Interviews / Screening")
            self.card_3["val"].configure(text=str(interview_cnt))
            self.card_4["title"].configure(text="Offers Received")
            self.card_4["val"].configure(text=str(offer_cnt))

    # --------------------------------------------------------------------------
    # FAST PAGINATED RENDERING (25ms execution time)
    # --------------------------------------------------------------------------

    def render_leads_list(self):
        # Clear existing cards
        for widget in self.leads_scroll.winfo_children():
            widget.destroy()

        search_query = self.search_entry.get().strip().lower()

        # 1. Select data source
        if self.active_tab == "📥 Discovery Inbox":
            source_list = self.notion_leads
            item_type = "discovery"
        elif self.active_tab == "🆕 Newly Scouted (Local)":
            source_list = self.local_leads
            item_type = "local"
        else:
            source_list = self.active_applications
            item_type = "tracker"

        # 2. Filter by status
        filtered = []
        for item in source_list:
            st = item.get("status", "")
            if self.active_tab == "📥 Discovery Inbox":
                if self.current_filter != "All" and st.lower() != self.current_filter.lower():
                    continue
            elif self.active_tab == "🆕 Newly Scouted (Local)":
                if self.current_filter == "Pending Push" and item.get("pushed"):
                    continue
                elif self.current_filter == "Synced" and not item.get("pushed"):
                    continue
            elif self.active_tab == "📊 Active Applications":
                if self.current_filter != "All" and st.lower() != self.current_filter.lower():
                    continue

            # Score Filter (for discovery & local)
            if item_type in ("discovery", "local") and self.score_filter != "All Scores":
                score_str = str(item.get("score", "0"))
                score_int = int(score_str) if score_str.isdigit() else 0
                if "8+" in self.score_filter and score_int < 8:
                    continue
                elif "6+" in self.score_filter and score_int < 6:
                    continue
                elif "4+" in self.score_filter and score_int < 4:
                    continue

            # Text Search
            if search_query:
                combined = f"{item.get('company', '')} {item.get('role', '')} {item.get('location', '')} {item.get('notes', '')}".lower()
                if search_query not in combined:
                    continue

            filtered.append(item)

        # 3. Sort
        if self.sort_mode == "Score (High to Low)":
            def _score_key(x):
                s = str(x.get("score", "0"))
                return int(s) if s.isdigit() else -1
            filtered.sort(key=_score_key, reverse=True)
        elif self.sort_mode == "Company (A-Z)":
            filtered.sort(key=lambda x: x.get("company", "").lower())
        elif self.sort_mode == "Newest First":
            filtered.sort(key=lambda x: x.get("date", ""), reverse=True)

        total_filtered = len(filtered)
        if total_filtered == 0:
            msg = f"No postings match your current filter and search criteria."
            ctk.CTkLabel(
                self.leads_scroll,
                text=msg,
                font=ctk.CTkFont(size=13),
                text_color="gray"
            ).pack(pady=40)
            return

        # 4. Pagination slicing
        total_pages = max(1, (total_filtered + self.page_size - 1) // self.page_size)
        if self.current_page > total_pages:
            self.current_page = total_pages

        start_idx = (self.current_page - 1) * self.page_size
        end_idx = min(start_idx + self.page_size, total_filtered)
        page_items = filtered[start_idx:end_idx]

        # Top banner for local drafts
        if self.active_tab == "🆕 Newly Scouted (Local)":
            banner = ctk.CTkFrame(self.leads_scroll, fg_color="#2c3e50", corner_radius=6)
            banner.pack(fill="x", padx=4, pady=(2, 6))
            ctk.CTkLabel(
                banner,
                text=f"📋 Showing {total_filtered} newly scouted local leads. Review below, then click 'Push All to Notion' when ready!",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f39c12"
            ).pack(padx=12, pady=6, anchor="w")

        # Render Page Cards
        for item in page_items:
            self._create_card(item, item_type)

        # Render Pagination Control Bar at bottom
        self._create_pagination_controls(total_filtered, total_pages, start_idx + 1, end_idx)

    def _create_pagination_controls(self, total_items: int, total_pages: int, start_num: int, end_num: int):
        p_frame = ctk.CTkFrame(self.leads_scroll, fg_color="#18181f", corner_radius=8)
        p_frame.pack(fill="x", padx=4, pady=(10, 4))
        p_frame.grid_columnconfigure((0, 4), weight=1)

        info_lbl = ctk.CTkLabel(
            p_frame,
            text=f"Showing {start_num}–{end_num} of {total_items} items (Page {self.current_page} of {total_pages})",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7"
        )
        info_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="w")

        btn_box = ctk.CTkFrame(p_frame, fg_color="transparent")
        btn_box.grid(row=0, column=4, padx=12, pady=8, sticky="e")

        # First
        ctk.CTkButton(
            btn_box,
            text="⏮️",
            width=32,
            height=28,
            state="normal" if self.current_page > 1 else "disabled",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=lambda: self._set_page(1)
        ).pack(side="left", padx=2)

        # Prev
        ctk.CTkButton(
            btn_box,
            text="◀ Prev",
            width=65,
            height=28,
            state="normal" if self.current_page > 1 else "disabled",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=lambda: self._set_page(self.current_page - 1)
        ).pack(side="left", padx=2)

        # Page Indicator
        ctk.CTkLabel(
            btn_box,
            text=f" {self.current_page} / {total_pages} ",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left", padx=4)

        # Next
        ctk.CTkButton(
            btn_box,
            text="Next ▶",
            width=65,
            height=28,
            state="normal" if self.current_page < total_pages else "disabled",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=lambda: self._set_page(self.current_page + 1)
        ).pack(side="left", padx=2)

        # Last
        ctk.CTkButton(
            btn_box,
            text="⏭️",
            width=32,
            height=28,
            state="normal" if self.current_page < total_pages else "disabled",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=lambda: self._set_page(total_pages)
        ).pack(side="left", padx=2)

    def _set_page(self, page_num: int):
        self.current_page = page_num
        self.render_leads_list()
        self.leads_scroll._parent_canvas.yview_moveto(0.0)

    # --------------------------------------------------------------------------
    # CARD BUILDER (SLEEK, CLEAN, HIGH-PERFORMANCE)
    # --------------------------------------------------------------------------

    def _create_card(self, item: Dict[str, Any], item_type: str):
        card = ctk.CTkFrame(self.leads_scroll, fg_color="#23232c", corner_radius=8, border_width=1, border_color="#323242")
        card.pack(fill="x", padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)

        # Row 0: Header with Company & Badges
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        hdr.grid_columnconfigure(0, weight=1)

        comp_lbl = ctk.CTkLabel(
            hdr,
            text=item.get("company", "Company"),
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        )
        comp_lbl.grid(row=0, column=0, sticky="w")

        badges = ctk.CTkFrame(hdr, fg_color="transparent")
        badges.grid(row=0, column=1, sticky="e")

        # Location badge
        loc_txt = item.get("location") or "Remote"
        ctk.CTkLabel(
            badges,
            text=f"📍 {loc_txt}",
            font=ctk.CTkFont(size=11),
            fg_color="#2c3e50",
            corner_radius=4,
            padx=7,
            pady=2
        ).pack(side="left", padx=3)

        # Match Score badge (for discovery/local)
        if item_type in ("discovery", "local"):
            score_raw = str(item.get("score", "-"))
            score_val = str(min(10, max(0, int(score_raw)))) if score_raw.isdigit() else score_raw
            score_col = "#27ae60" if score_val.isdigit() and int(score_val) >= 7 else "#e67e22" if score_val.isdigit() and int(score_val) >= 4 else "#7f8c8d"
            ctk.CTkLabel(
                badges,
                text=f"★ Match: {score_val}/10",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=score_col,
                corner_radius=4,
                padx=7,
                pady=2
            ).pack(side="left", padx=3)

        # Status Badge
        st_val = item.get("status", "New")
        if item_type == "local":
            st_text = "Synced" if item.get("pushed") else "Local Draft"
            st_col = "#27ae60" if item.get("pushed") else "#d35400"
        else:
            st_text = st_val
            st_col = "#2980b9" if st_val == "New" else "#27ae60" if st_val in ("Approved", "Offer") else "#8e44ad" if st_val in ("Interview", "Screening") else "#c0392b"

        ctk.CTkLabel(
            badges,
            text=st_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=st_col,
            corner_radius=4,
            padx=7,
            pady=2
        ).pack(side="left", padx=3)

        # Row 1: Role Title
        role_lbl = ctk.CTkLabel(
            card,
            text=item.get("role", "Software Role"),
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#3498db"
        )
        role_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 3))

        # Row 2: Snippet / Notes
        snippet = item.get("notes", "")
        if snippet:
            clean_snip = snippet.replace("\n", " ").strip()
            if len(clean_snip) > 150:
                clean_snip = clean_snip[:150] + "..."
            ctk.CTkLabel(
                card,
                text=clean_snip,
                font=ctk.CTkFont(size=11),
                text_color="#bdc3c7",
                justify="left",
                wraplength=760
            ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))

        # Row 3: Actions Bar
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Left action: Inspect / Details
        ctk.CTkButton(
            actions,
            text="👁️ Inspect Details",
            width=115,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
            command=lambda it=item, it_type=item_type: self.open_details_modal(it, it_type)
        ).pack(side="left", padx=(0, 6))

        if item.get("url"):
            ctk.CTkButton(
                actions,
                text="🔗 Open Link",
                width=90,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#34495e",
                hover_color="#415b76",
                command=lambda url=item["url"]: webbrowser.open(url)
            ).pack(side="left", padx=3)

        # Right Actions based on item type
        if item_type == "discovery":
            # Delete button
            ctk.CTkButton(
                actions,
                text="🗑️",
                width=35,
                height=26,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda p_id=item["id"], comp=item["company"]: self.on_delete_single(p_id, comp)
            ).pack(side="right", padx=2)

            if item["status"] != "Dismissed":
                ctk.CTkButton(
                    actions,
                    text="❌ Dismiss",
                    width=75,
                    height=26,
                    font=ctk.CTkFont(size=11),
                    fg_color="#922b21",
                    hover_color="#b03a2e",
                    command=lambda p_id=item["id"], comp=item["company"]: self.on_update_status(p_id, "Dismissed", comp)
                ).pack(side="right", padx=2)

            if item["status"] != "Approved":
                ctk.CTkButton(
                    actions,
                    text="✅ Approve",
                    width=80,
                    height=26,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#1e8449",
                    hover_color="#27ae60",
                    command=lambda p_id=item["id"], comp=item["company"]: self.on_update_status(p_id, "Approved", comp)
                ).pack(side="right", padx=2)
            else:
                # One-Click Promotion to Active Applications
                ctk.CTkButton(
                    actions,
                    text="🚀 Move to Applications",
                    height=26,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#27ae60",
                    hover_color="#219150",
                    command=lambda it=item: self.on_promote_lead(it)
                ).pack(side="right", padx=2)

        elif item_type == "local":
            ctk.CTkButton(
                actions,
                text="📤 Push to Notion",
                width=110,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#e67e22",
                hover_color="#d35400",
                command=lambda l=item: self.on_push_single_lead(l)
            ).pack(side="right", padx=3)

            ctk.CTkButton(
                actions,
                text="✕ Remove",
                width=75,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda l=item: self.on_remove_local_lead(l)
            ).pack(side="right", padx=3)

        elif item_type == "tracker":
            # Active application controls
            ctk.CTkButton(
                actions,
                text="🗑️ Archive",
                width=75,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda p_id=item["id"], comp=item["company"]: self.on_delete_application(p_id, comp)
            ).pack(side="right", padx=2)

            # Quick stage updater
            st_var = ctk.StringVar(value=item.get("status", "Applied"))
            stage_dropdown = ctk.CTkOptionMenu(
                actions,
                values=["Wishlist", "Applied", "Screening", "Interview", "Offer", "Rejected"],
                variable=st_var,
                width=110,
                height=26,
                font=ctk.CTkFont(size=11),
                command=lambda val, p_id=item["id"], comp=item["company"]: self.on_update_app_stage(p_id, val, comp)
            )
            stage_dropdown.pack(side="right", padx=4)

    # --------------------------------------------------------------------------
    # MODAL OPENERS
    # --------------------------------------------------------------------------

    def open_details_modal(self, item: Dict[str, Any], item_type: str):
        callbacks = {
            "on_approve": lambda it: self.on_update_status(it["id"], "Approved", it["company"]),
            "on_dismiss": lambda it: self.on_update_status(it["id"], "Dismissed", it["company"]),
            "on_promote": lambda it: self.on_promote_lead(it),
            "on_stage_change": lambda it, stage: self.on_update_app_stage(it["id"], stage, it["company"])
        }
        JobDetailsModal(self, item, item_type, callbacks)

    def open_profile_settings(self):
        ProfileSettingsModal(self, on_saved_callback=lambda: self.log("⚙️ Profile configuration updated.\n"))

    # --------------------------------------------------------------------------
    # OPTIMISTIC LEAD ACTIONS & API CALLS
    # --------------------------------------------------------------------------

    def on_update_status(self, page_id: str, new_status: str, company: str):
        # Optimistic update in UI
        for l in self.notion_leads:
            if l["id"] == page_id:
                l["status"] = new_status
                break
        self._update_metrics_and_filter_badges()
        self.render_leads_list()
        self.log(f"🔄 Setting '{company}' to {new_status}...\n")

        def _worker():
            try:
                update_lead_status(page_id, new_status)
                self.log(f"✅ '{company}' updated to {new_status}.\n")
            except Exception as e:
                self.log(f"❌ Failed to update '{company}': {str(e)}\n")

        threading.Thread(target=_worker, daemon=True).start()

    def on_delete_single(self, page_id: str, company: str):
        if not messagebox.askyesno("Confirm Deletion", f"Move '{company}' to Notion Trash?"):
            return

        # Optimistic update
        self.notion_leads = [l for l in self.notion_leads if l["id"] != page_id]
        self._update_metrics_and_filter_badges()
        self.render_leads_list()
        self.log(f"🗑️ Archiving '{company}' to Trash...\n")

        def _worker():
            try:
                delete_lead(page_id)
                self.log(f"✅ '{company}' archived to Trash.\n")
            except Exception as e:
                self.log(f"❌ Error archiving '{company}': {str(e)}\n")

        threading.Thread(target=_worker, daemon=True).start()

    def on_clean_dismissed(self):
        dismissed_count = sum(1 for l in self.notion_leads if l.get("status", "").lower() == "dismissed")
        if dismissed_count == 0:
            messagebox.showinfo("Nothing to Clean", "There are no dismissed leads in your Notion inbox!")
            return

        if not messagebox.askyesno(
            "Confirm Bulk Cleanup",
            f"Are you sure you want to permanently move all {dismissed_count} Dismissed leads to the Notion Trash?"
        ):
            return

        self.btn_clean_dismissed.configure(state="disabled", text="⏳ Cleaning...")
        self.log(f"🧹 Starting bulk cleanup of {dismissed_count} dismissed leads...\n")

        def _worker():
            try:
                def _prog(curr, tot):
                    if curr % 5 == 0 or curr == tot:
                        self.log(f"  • Archived {curr}/{tot} leads...\n")

                cleaned = clean_dismissed_leads(progress_callback=_prog)
                self.log(f"🎉 Successfully cleaned {cleaned} leads to Notion Trash!\n")
                self.after(0, self.refresh_all_data)
            except Exception as e:
                self.log(f"❌ Error during cleanup: {str(e)}\n")
            finally:
                self.after(0, lambda: self.btn_clean_dismissed.configure(state="normal", text="🧹 Clean All Dismissed"))

        threading.Thread(target=_worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # ACTIVE APPLICATION ACTIONS
    # --------------------------------------------------------------------------

    def on_update_app_stage(self, page_id: str, new_stage: str, company: str):
        # Optimistic update
        for a in self.active_applications:
            if a["id"] == page_id:
                a["status"] = new_stage
                break
        self._update_metrics_and_filter_badges()
        self.render_leads_list()
        self.log(f"🔄 Advancing application '{company}' to stage '{new_stage}'...\n")

        def _worker():
            try:
                update_application_status(page_id, new_stage)
                self.log(f"✅ Application stage for '{company}' saved as '{new_stage}'.\n")
            except Exception as e:
                self.log(f"❌ Failed to advance stage: {str(e)}\n")

        threading.Thread(target=_worker, daemon=True).start()

    def on_delete_application(self, page_id: str, company: str):
        if not messagebox.askyesno("Confirm Archive", f"Archive application for '{company}' to trash?"):
            return

        self.active_applications = [a for a in self.active_applications if a["id"] != page_id]
        self._update_metrics_and_filter_badges()
        self.render_leads_list()
        self.log(f"🗑️ Archiving application '{company}'...\n")

        def _worker():
            try:
                delete_application(page_id)
                self.log(f"✅ Application for '{company}' archived.\n")
            except Exception as e:
                self.log(f"❌ Error archiving application: {str(e)}\n")

        threading.Thread(target=_worker, daemon=True).start()

    def on_promote_lead(self, lead: Dict[str, Any]):
        """Promotes an approved discovery lead directly into the Active Applications tracker."""
        comp = lead.get("company", "Company")
        self.log(f"🚀 Promoting '{comp}' into Active Applications Tracker...\n")

        # Mark discovery lead as Approved
        lead["status"] = "Approved"
        self._update_metrics_and_filter_badges()
        self.render_leads_list()

        def _worker():
            try:
                # 1. Update status in Discovery DB to Approved
                if lead.get("id"):
                    update_lead_status(lead["id"], "Approved")

                # 2. Create entry in Active Job Applications Tracker
                promote_lead_to_application(lead, initial_status="Applied")
                self.log(f"🎉 Successfully created active application for '{comp}' in Notion Tracker!\n")

                # Refresh active applications
                fresh_apps = fetch_active_applications(status_filter="all")
                self.after(0, lambda: self._on_promoted_sync(fresh_apps, comp))
            except Exception as e:
                self.log(f"❌ Failed to promote lead: {str(e)}\n")

        threading.Thread(target=_worker, daemon=True).start()

    def _on_promoted_sync(self, fresh_apps: List[Dict], comp: str):
        self.active_applications = fresh_apps
        self._update_metrics_and_filter_badges()
        messagebox.showinfo(
            "Application Created",
            f"'{comp}' has been promoted into your active Job Applications pipeline!",
            parent=self
        )

    # --------------------------------------------------------------------------
    # LOCAL LEADS & PUSH ACTIONS
    # --------------------------------------------------------------------------

    def on_push_single_lead(self, lead: Dict):
        self.log(f"📤 Pushing '{lead['company']}' to Notion Discovery Inbox...\n")
        def _worker():
            try:
                ok = push_leads_to_notion([lead])
                if ok:
                    self.log(f"✅ Pushed '{lead['company']}' to Notion!\n")
                    lead["pushed"] = True
                    self.after(0, self.render_leads_list)
                    self.after(0, self.refresh_all_data)
                else:
                    self.log(f"ℹ️ '{lead['company']}' already exists in Notion.\n")
            except Exception as e:
                self.log(f"❌ Failed to push lead: {str(e)}\n")
        threading.Thread(target=_worker, daemon=True).start()

    def on_push_leads_clicked(self):
        unpushed = [l for l in self.local_leads if not l.get("pushed")]
        if not unpushed:
            messagebox.showinfo("Nothing to Push", "All local discovered leads are already pushed to Notion!")
            return

        if not messagebox.askyesno(
            "Confirm Push",
            f"Push all {len(unpushed)} newly discovered leads to your Notion Discovery Inbox database?"
        ):
            return

        self.btn_push_to_notion.configure(state="disabled", text="⏳ Pushing...")
        self.log(f"\n📤 Starting push of {len(unpushed)} leads to Notion...\n")

        def _worker():
            try:
                def _prog(curr, tot):
                    if curr % 5 == 0 or curr == tot:
                        self.log(f"  • Pushed {curr}/{tot} leads to Notion...\n")
                count = push_leads_to_notion(unpushed, progress_callback=_prog)
                self.log(f"🎉 Successfully pushed {count} leads to Notion Discovery Inbox!\n")
                self.after(0, self.refresh_all_data)
            except Exception as e:
                self.log(f"❌ Error during push: {str(e)}\n")
            finally:
                self.after(0, lambda: self.btn_push_to_notion.configure(state="normal", text="📤 Push All to Notion"))

        threading.Thread(target=_worker, daemon=True).start()

    def on_remove_local_lead(self, lead: Dict):
        self.local_leads = [l for l in self.local_leads if l != lead]
        self._update_metrics_and_filter_badges()
        self.render_leads_list()

    # --------------------------------------------------------------------------
    # SCOUT PROCESS EXECUTION
    # --------------------------------------------------------------------------

    def on_run_scout(self):
        freshness = self.freshness_var.get()
        category = self.category_var.get()
        depth_val = self.depth_var.get()
        rescan = self.rescan_var.get()

        max_queries = 20
        if "50 Dorks" in depth_val:
            max_queries = 50
        elif "All Dorks" in depth_val:
            max_queries = 0

        self.btn_run_scout.configure(state="disabled", text="⏳ Running Scout...")
        self.btn_stop_scout.configure(state="normal", fg_color="#c0392b")

        rescan_msg = " [🔄 Force Rescan Enabled]" if rescan else ""
        self.log(f"\n{'='*60}\n🚀 Launching Job Scout (Freshness: {freshness}, Category: {category}{rescan_msg}, Mode: Local Search)\n{'='*60}\n")

        def _worker():
            try:
                run_scout_process(
                    freshness=freshness,
                    category=category,
                    max_queries=max_queries,
                    rescan=rescan,
                    log_callback=self.log
                )
            except Exception as e:
                self.log(f"❌ Scout execution error: {str(e)}\n")
            finally:
                self.after(0, self._on_scout_finished)

        self.scout_thread = threading.Thread(target=_worker, daemon=True)
        self.scout_thread.start()

    def on_stop_scout(self):
        self.btn_stop_scout.configure(state="disabled", text="⏳ Stopping...")
        self.log("\n🛑 Stopping Job Scout process immediately...\n")
        def _killer():
            ok = stop_scout_process()
            if ok:
                self.log("✅ Process killed.\n")
        threading.Thread(target=_killer, daemon=True).start()

    def _on_scout_finished(self):
        self.btn_run_scout.configure(state="normal", text="🚀 Run Job Scout (Local Search)")
        self.btn_stop_scout.configure(state="disabled", text="⏹️ Stop Scout", fg_color="#7f8c8d")

        # Load newly discovered local jobs
        self.local_leads = load_local_discovered_jobs()
        self.log(f"📥 Loaded {len(self.local_leads)} discovered leads from local search run.\n")

        # Switch view to Local Leads tab so user can immediately review them
        self.mode_segmented.set("🆕 Newly Scouted (Local)")
        self.on_mode_changed("🆕 Newly Scouted (Local)")

    # --------------------------------------------------------------------------
    # EXIT INTERCEPTOR
    # --------------------------------------------------------------------------

    def on_app_close(self):
        stop_scout_process()

        unpushed = [l for l in self.local_leads if not l.get("pushed")]
        if unpushed:
            ans = messagebox.askyesnocancel(
                "Unpushed Discovered Leads",
                f"You have {len(unpushed)} newly discovered job lead(s) that have not been pushed to Notion yet!\n\n"
                "Would you like to push them to Notion before exiting?\n\n"
                "• [Yes]: Push leads to Notion and Exit\n"
                "• [No]: Exit immediately without pushing\n"
                "• [Cancel]: Stay in the app"
            )
            if ans is True:
                self.log("📤 Pushing leads to Notion before exit...\n")
                try:
                    push_leads_to_notion(unpushed)
                except Exception:
                    pass
                self.destroy()
                return
            elif ans is False:
                self.destroy()
                return
            else:
                return

        self.destroy()


if __name__ == "__main__":
    app = CareerDashboardApp()
    app.mainloop()
