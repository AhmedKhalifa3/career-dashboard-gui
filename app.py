"""
Career Cockpit — Autonomous Job Scout & Notion Dashboard
A modern CustomTkinter desktop GUI for managing autonomous job discovery,
scoring, triage, and Notion database lifecycle.
"""

import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from typing import Dict, List, Optional
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
    get_discovery_db_id
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CareerDashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Career Cockpit — Autonomous Job Scout & Notion Dashboard")
        self.geometry("1240x840")
        self.minsize(1050, 700)

        # Application state
        self.notion_leads: List[Dict] = []
        self.local_leads: List[Dict] = []
        self.active_tab = "Notion Inbox"
        self.current_filter = "New"
        self.is_loading = False
        self.is_pushing = False
        self.scout_thread: Optional[threading.Thread] = None

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_view()

        # Intercept window close to remind about unpushed leads
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # Initial load
        self.after(200, self.initial_load)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(18, weight=1)

        # Branding
        title_lbl = ctk.CTkLabel(
            self.sidebar,
            text="💼 Career Cockpit",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(20, 2), sticky="w")

        subtitle_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Autonomous Lead Discovery & Triage",
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
        self.depth_menu.grid(row=9, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Scout Action Buttons
        self.btn_run_scout = ctk.CTkButton(
            self.sidebar,
            text="🚀 Run Job Scout (Local Search)",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
            command=self.on_run_scout
        )
        self.btn_run_scout.grid(row=10, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_stop_scout = ctk.CTkButton(
            self.sidebar,
            text="⏹️ Stop Scout",
            fg_color="#7f8c8d",
            hover_color="#c0392b",
            state="disabled",
            command=self.on_stop_scout
        )
        self.btn_stop_scout.grid(row=11, column=0, padx=20, pady=(0, 15), sticky="ew")

        sep2 = ctk.CTkProgressBar(self.sidebar, height=2)
        sep2.set(1.0)
        sep2.grid(row=12, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Database Management Section
        maint_hdr = ctk.CTkLabel(
            self.sidebar,
            text="DATABASE MAINTENANCE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#9b59b6"
        )
        maint_hdr.grid(row=13, column=0, padx=20, pady=(0, 8), sticky="w")

        self.btn_refresh = ctk.CTkButton(
            self.sidebar,
            text="🔄 Refresh Notion Inbox",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self.refresh_leads
        )
        self.btn_refresh.grid(row=14, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_clean_dismissed = ctk.CTkButton(
            self.sidebar,
            text="🧹 Clean All Dismissed",
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            command=self.on_clean_dismissed
        )
        self.btn_clean_dismissed.grid(row=15, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Bottom theme toggle
        theme_lbl = ctk.CTkLabel(self.sidebar, text="Appearance Mode:", font=ctk.CTkFont(size=11))
        theme_lbl.grid(row=19, column=0, padx=20, pady=(10, 0), sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode
        )
        self.theme_menu.grid(row=20, column=0, padx=20, pady=(2, 20), sticky="ew")

    def _build_main_view(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(3, weight=3) # Leads list
        self.main_container.grid_rowconfigure(4, weight=1) # Log Console

        # Top Bar: Metrics Cards
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.top_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total = self._create_metric_card(self.top_bar, 0, "Total In Notion", "0", "#34495e")
        self.card_new = self._create_metric_card(self.top_bar, 1, "New Awaiting Review", "0", "#2980b9")
        self.card_approved = self._create_metric_card(self.top_bar, 2, "Approved Leads", "0", "#27ae60")
        self.card_local_pending = self._create_metric_card(self.top_bar, 3, "🆕 Local (Pending Push)", "0", "#d35400")

        # Primary Mode Navigation (Notion Inbox vs Newly Discovered Local Leads)
        self.nav_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.nav_bar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.nav_bar.grid_columnconfigure(0, weight=1)

        self.mode_segmented = ctk.CTkSegmentedButton(
            self.nav_bar,
            values=["📥 Notion Discovery Inbox", "🆕 Newly Discovered (Local / Pending Push)"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_mode_changed
        )
        self.mode_segmented.set("📥 Notion Discovery Inbox")
        self.mode_segmented.grid(row=0, column=0, sticky="ew")

        # Sub-Controls Bar (Filter pills, Push button, Search)
        self.controls_bar = ctk.CTkFrame(self.main_container)
        self.controls_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=2)
        self.controls_bar.grid_columnconfigure(1, weight=1)

        # Tab Segmented Button for Notion Inbox
        self.tab_filter = ctk.CTkSegmentedButton(
            self.controls_bar,
            values=["New", "Approved", "Dismissed", "All"],
            command=self.on_filter_changed
        )
        self.tab_filter.set("New")
        self.tab_filter.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        # Push to Notion Button (Visible / active when viewing local leads)
        self.btn_push_to_notion = ctk.CTkButton(
            self.controls_bar,
            text="📤 Push All to Notion",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#e67e22",
            hover_color="#d35400",
            command=self.on_push_leads_clicked
        )
        self.btn_push_to_notion.grid(row=0, column=2, padx=10, pady=8, sticky="e")

        # Quick Search Box
        self.search_entry = ctk.CTkEntry(
            self.controls_bar,
            placeholder_text="🔍 Filter by company, title, or location...",
            height=32
        )
        self.search_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.render_leads_list())

        # Leads Scrollable Area
        self.leads_scroll = ctk.CTkScrollableFrame(self.main_container, label_text="Job Postings")
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

        return val_lbl

    def log(self, message: str):
        def _append():
            self.console_text.insert("end", message)
            self.console_text.see("end")
        self.after(0, _append)

    def clear_console(self):
        self.console_text.delete("1.0", "end")

    def initial_load(self):
        self.local_leads = load_local_discovered_jobs()
        self.card_local_pending.configure(text=str(len(self.local_leads)))
        self.refresh_leads()

    # --- Mode & Tab Switching ---

    def on_mode_changed(self, mode_value):
        if "Notion" in mode_value:
            self.active_tab = "Notion Inbox"
            self.tab_filter.grid()
            self.btn_push_to_notion.configure(state="disabled")
        else:
            self.active_tab = "Local Leads"
            self.tab_filter.grid_remove()
            self.btn_push_to_notion.configure(state="normal")
        self.render_leads_list()

    def on_filter_changed(self, value):
        self.current_filter = value
        self.render_leads_list()

    # --- Data Rendering ---

    def render_leads_list(self):
        for widget in self.leads_scroll.winfo_children():
            widget.destroy()

        search_query = self.search_entry.get().strip().lower()

        if self.active_tab == "Notion Inbox":
            source_list = self.notion_leads
            filter_mode = self.current_filter
        else:
            source_list = self.local_leads
            filter_mode = "All"

        filtered = []
        for l in source_list:
            if self.active_tab == "Notion Inbox" and filter_mode != "All":
                if l["status"].lower() != filter_mode.lower():
                    continue
            if search_query:
                combined_txt = f"{l['company']} {l['role']} {l['location']} {l.get('notes', '')}".lower()
                if search_query not in combined_txt:
                    continue
            filtered.append(l)

        if not filtered:
            msg = (
                f"No postings found in Notion Inbox for '{self.current_filter}'."
                if self.active_tab == "Notion Inbox"
                else "No local discovered jobs found. Click 'Run Job Scout' to search!"
            )
            empty_lbl = ctk.CTkLabel(
                self.leads_scroll,
                text=msg,
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            return

        # Banner if showing local leads
        if self.active_tab == "Local Leads":
            banner = ctk.CTkFrame(self.leads_scroll, fg_color="#2c3e50", corner_radius=6)
            banner.pack(fill="x", padx=4, pady=(2, 8))
            banner.grid_columnconfigure(0, weight=1)

            b_lbl = ctk.CTkLabel(
                banner,
                text=f"📋 Showing {len(filtered)} newly scouted leads stored locally. Review below, then click 'Push to Notion' when satisfied!",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f39c12"
            )
            b_lbl.grid(row=0, column=0, padx=12, pady=8, sticky="w")

        for lead in filtered:
            self._create_lead_card(lead, is_local=(self.active_tab == "Local Leads"))

    def _create_lead_card(self, lead: Dict, is_local: bool = False):
        card = ctk.CTkFrame(self.leads_scroll, fg_color="#2b2b36", corner_radius=8)
        card.pack(fill="x", padx=4, pady=5)
        card.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        header_frame.grid_columnconfigure(0, weight=1)

        company_lbl = ctk.CTkLabel(
            header_frame,
            text=lead["company"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        company_lbl.grid(row=0, column=0, sticky="w")

        badge_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        badge_frame.grid(row=0, column=1, sticky="e")

        # Location badge
        loc_badge = ctk.CTkLabel(
            badge_frame,
            text=f"📍 {lead['location']}",
            font=ctk.CTkFont(size=11),
            fg_color="#3a3a4c",
            corner_radius=4,
            padx=8,
            pady=2
        )
        loc_badge.pack(side="left", padx=3)

        # Score badge
        score_val = str(lead.get("score", "-"))
        score_color = "#27ae60" if score_val.isdigit() and int(score_val) >= 5 else "#e67e22" if score_val.isdigit() and int(score_val) >= 3 else "#7f8c8d"
        score_badge = ctk.CTkLabel(
            badge_frame,
            text=f"★ Match: {score_val}/10",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=score_color,
            corner_radius=4,
            padx=8,
            pady=2
        )
        score_badge.pack(side="left", padx=3)

        # Status badge
        if not is_local:
            st_color = "#2980b9" if lead["status"] == "New" else "#27ae60" if lead["status"] == "Approved" else "#c0392b"
            status_badge = ctk.CTkLabel(
                badge_frame,
                text=lead["status"],
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=st_color,
                corner_radius=4,
                padx=8,
                pady=2
            )
            status_badge.pack(side="left", padx=3)
        else:
            pushed_lbl = ctk.CTkLabel(
                badge_frame,
                text="Synced to Notion" if lead.get("pushed") else "Local Draft",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#27ae60" if lead.get("pushed") else "#d35400",
                corner_radius=4,
                padx=8,
                pady=2
            )
            pushed_lbl.pack(side="left", padx=3)

        # Role Title
        role_lbl = ctk.CTkLabel(
            card,
            text=lead["role"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ecf0f1"
        )
        role_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))

        # Snippet
        snippet = lead.get("notes", "")
        if snippet:
            snippet_clean = snippet.replace("\n", " ")[:160] + ("..." if len(snippet) > 160 else "")
            notes_lbl = ctk.CTkLabel(
                card,
                text=snippet_clean,
                font=ctk.CTkFont(size=11),
                text_color="#bdc3c7",
                justify="left",
                wraplength=750
            )
            notes_lbl.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

        # Actions Frame
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

        if lead.get("url"):
            btn_open = ctk.CTkButton(
                actions_frame,
                text="🔗 Open Job Link",
                width=110,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#34495e",
                hover_color="#415b76",
                command=lambda url=lead["url"]: webbrowser.open(url)
            )
            btn_open.pack(side="left", padx=(0, 8))

        if is_local:
            # Action for local leads
            btn_push_single = ctk.CTkButton(
                actions_frame,
                text="📤 Push to Notion",
                width=110,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#e67e22",
                hover_color="#d35400",
                command=lambda l=lead: self.on_push_single_lead(l)
            )
            btn_push_single.pack(side="right", padx=3)

            btn_del_local = ctk.CTkButton(
                actions_frame,
                text="✕ Remove",
                width=75,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda l=lead: self.on_remove_local_lead(l)
            )
            btn_del_local.pack(side="right", padx=3)
        else:
            # Actions for Notion leads
            btn_trash = ctk.CTkButton(
                actions_frame,
                text="🗑️ Trash",
                width=70,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda p_id=lead["id"], comp=lead["company"]: self.on_delete_single(p_id, comp)
            )
            btn_trash.pack(side="right", padx=3)

            if lead["status"] != "Dismissed":
                btn_dismiss = ctk.CTkButton(
                    actions_frame,
                    text="❌ Dismiss",
                    width=80,
                    height=26,
                    font=ctk.CTkFont(size=11),
                    fg_color="#922b21",
                    hover_color="#b03a2e",
                    command=lambda p_id=lead["id"], comp=lead["company"]: self.on_update_status(p_id, "Dismissed", comp)
                )
                btn_dismiss.pack(side="right", padx=3)

            if lead["status"] != "Approved":
                btn_approve = ctk.CTkButton(
                    actions_frame,
                    text="✅ Approve",
                    width=85,
                    height=26,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#1e8449",
                    hover_color="#27ae60",
                    command=lambda p_id=lead["id"], comp=lead["company"]: self.on_update_status(p_id, "Approved", comp)
                )
                btn_approve.pack(side="right", padx=3)

    # --- Push to Notion Handlers ---

    def on_push_single_lead(self, lead: Dict):
        self.log(f"📤 Pushing '{lead['company']}' to Notion Discovery Inbox...\n")
        def _worker():
            try:
                ok = push_leads_to_notion([lead])
                if ok:
                    self.log(f"✅ Pushed '{lead['company']}' to Notion!\n")
                    lead["pushed"] = True
                    self.after(0, self.render_leads_list)
                    self.after(0, self.refresh_leads)
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
                self.after(0, self.render_leads_list)
                self.after(0, self.refresh_leads)
            except Exception as e:
                self.log(f"❌ Error during push: {str(e)}\n")
            finally:
                self.after(0, lambda: self.btn_push_to_notion.configure(state="normal", text="📤 Push All to Notion"))

        threading.Thread(target=_worker, daemon=True).start()

    def on_remove_local_lead(self, lead: Dict):
        self.local_leads = [l for l in self.local_leads if l != lead]
        self.card_local_pending.configure(text=str(len(self.local_leads)))
        self.render_leads_list()

    # --- Notion Lead Actions ---

    def refresh_leads(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.configure(state="disabled", text="⏳ Loading...")
        self.log(f"🔄 Fetching leads from Notion ({get_discovery_db_id()[:8]}...)\n")

        def _worker():
            try:
                all_leads = fetch_discovered_leads(status_filter="all")
                self.after(0, lambda: self._on_leads_loaded(all_leads))
            except Exception as e:
                self.after(0, lambda: self._on_leads_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_leads_loaded(self, leads: List[Dict]):
        self.notion_leads = leads
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh Notion Inbox")

        total = len(leads)
        new_cnt = sum(1 for l in leads if l["status"].lower() == "new")
        app_cnt = sum(1 for l in leads if l["status"].lower() == "approved")

        self.card_total.configure(text=str(total))
        self.card_new.configure(text=str(new_cnt))
        self.card_approved.configure(text=str(app_cnt))
        self.card_local_pending.configure(text=str(len([l for l in self.local_leads if not l.get("pushed")])))

        self.log(f"✅ Loaded {total} leads from Notion ({new_cnt} New, {app_cnt} Approved).\n")
        self.render_leads_list()

    def _on_leads_error(self, err_msg: str):
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh Notion Inbox")
        self.log(f"❌ Error fetching leads: {err_msg}\n")
        messagebox.showerror("Notion API Error", f"Failed to retrieve leads from Notion:\n\n{err_msg}")

    def on_update_status(self, page_id: str, new_status: str, company: str):
        self.log(f"🔄 Updating '{company}' status to {new_status}...\n")
        def _worker():
            try:
                update_lead_status(page_id, new_status)
                self.log(f"✅ Lead '{company}' marked as {new_status}.\n")
                for l in self.notion_leads:
                    if l["id"] == page_id:
                        l["status"] = new_status
                        break
                self.after(0, self.render_leads_list)
                self.after(0, self._recount_notion_metrics)
            except Exception as e:
                self.log(f"❌ Failed to update lead: {str(e)}\n")
        threading.Thread(target=_worker, daemon=True).start()

    def on_delete_single(self, page_id: str, company: str):
        if not messagebox.askyesno("Confirm Deletion", f"Move '{company}' to Notion Trash?"):
            return
        self.log(f"🗑️ Deleting '{company}' from Discovery Inbox...\n")
        def _worker():
            try:
                delete_lead(page_id)
                self.log(f"✅ Lead '{company}' archived to Trash.\n")
                self.notion_leads = [l for l in self.notion_leads if l["id"] != page_id]
                self.after(0, self.render_leads_list)
                self.after(0, self._recount_notion_metrics)
            except Exception as e:
                self.log(f"❌ Failed to delete lead: {str(e)}\n")
        threading.Thread(target=_worker, daemon=True).start()

    def _recount_notion_metrics(self):
        total = len(self.notion_leads)
        new_cnt = sum(1 for l in self.notion_leads if l["status"].lower() == "new")
        app_cnt = sum(1 for l in self.notion_leads if l["status"].lower() == "approved")
        self.card_total.configure(text=str(total))
        self.card_new.configure(text=str(new_cnt))
        self.card_approved.configure(text=str(app_cnt))

    def on_clean_dismissed(self):
        dismissed_count = sum(1 for l in self.notion_leads if l["status"].lower() == "dismissed")
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
                self.after(0, self.refresh_leads)
            except Exception as e:
                self.log(f"❌ Error during cleanup: {str(e)}\n")
            finally:
                self.after(0, lambda: self.btn_clean_dismissed.configure(state="normal", text="🧹 Clean All Dismissed"))

        threading.Thread(target=_worker, daemon=True).start()

    # --- Scout Process Execution ---

    def on_run_scout(self):
        freshness = self.freshness_var.get()
        category = self.category_var.get()
        depth_val = self.depth_var.get()

        max_queries = 20
        if "50 Dorks" in depth_val:
            max_queries = 50
        elif "All Dorks" in depth_val:
            max_queries = 0

        self.btn_run_scout.configure(state="disabled", text="⏳ Running Scout...")
        self.btn_stop_scout.configure(state="normal", fg_color="#c0392b")

        self.log(f"\n{'='*60}\n🚀 Launching Job Scout (Freshness: {freshness}, Category: {category}, Mode: Local Search)\n{'='*60}\n")

        def _worker():
            try:
                run_scout_process(
                    freshness=freshness,
                    category=category,
                    max_queries=max_queries,
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
        self.card_local_pending.configure(text=str(len(self.local_leads)))
        self.log(f"📥 Loaded {len(self.local_leads)} discovered leads from local search run.\n")

        # Switch view to Local Leads tab so user can immediately review them
        self.mode_segmented.set("🆕 Newly Discovered (Local / Pending Push)")
        self.on_mode_changed("🆕 Newly Discovered (Local / Pending Push)")

    # --- Application Exit Interceptor ---

    def on_app_close(self):
        # Stop any active scout
        stop_scout_process()

        # Check for unpushed leads
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
            if ans is True: # Yes
                self.log("📤 Pushing leads to Notion before exit...\n")
                try:
                    push_leads_to_notion(unpushed)
                except Exception:
                    pass
                self.destroy()
                return
            elif ans is False: # No
                self.destroy()
                return
            else: # Cancel
                return

        self.destroy()

if __name__ == "__main__":
    app = CareerDashboardApp()
    app.mainloop()
