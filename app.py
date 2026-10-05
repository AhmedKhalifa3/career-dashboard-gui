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
    get_discovery_db_id
)

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CareerDashboardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Career Cockpit — Autonomous Job Scout & Notion Dashboard")
        self.geometry("1220x820")
        self.minsize(1050, 700)

        # Application state
        self.leads: List[Dict] = []
        self.current_filter = "New"
        self.is_loading = False
        self.scout_thread: Optional[threading.Thread] = None
        self.scout_stop_event = threading.Event()

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_view()

        # Initial load
        self.after(200, self.refresh_leads)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(14, weight=1)

        # Branding
        title_lbl = ctk.CTkLabel(
            self.sidebar,
            text="💼 Career Cockpit",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_lbl.grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

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
        self.freshness_menu.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

        # Category
        c_lbl = ctk.CTkLabel(self.sidebar, text="Role Category:", font=ctk.CTkFont(size=12))
        c_lbl.grid(row=6, column=0, padx=20, pady=(2, 0), sticky="w")
        self.category_var = ctk.StringVar(value="all")
        self.category_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["all", "werkstudent", "ai_agent", "backend", "fullstack", "sdet_qa"],
            variable=self.category_var
        )
        self.category_menu.grid(row=7, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Scout Action Buttons
        self.btn_run_scout = ctk.CTkButton(
            self.sidebar,
            text="🚀 Run Job Scout",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#1f6aa5",
            hover_color="#144d75",
            command=self.on_run_scout
        )
        self.btn_run_scout.grid(row=8, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_stop_scout = ctk.CTkButton(
            self.sidebar,
            text="⏹️ Stop Scout",
            fg_color="#7f8c8d",
            hover_color="#95a5a6",
            state="disabled",
            command=self.on_stop_scout
        )
        self.btn_stop_scout.grid(row=9, column=0, padx=20, pady=(0, 15), sticky="ew")

        sep2 = ctk.CTkProgressBar(self.sidebar, height=2)
        sep2.set(1.0)
        sep2.grid(row=10, column=0, padx=20, pady=(5, 15), sticky="ew")

        # Database Management Section
        maint_hdr = ctk.CTkLabel(
            self.sidebar,
            text="DATABASE MAINTENANCE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#9b59b6"
        )
        maint_hdr.grid(row=11, column=0, padx=20, pady=(0, 8), sticky="w")

        self.btn_refresh = ctk.CTkButton(
            self.sidebar,
            text="🔄 Refresh Leads",
            fg_color="#2c3e50",
            hover_color="#34495e",
            command=self.refresh_leads
        )
        self.btn_refresh.grid(row=12, column=0, padx=20, pady=(0, 8), sticky="ew")

        self.btn_clean_dismissed = ctk.CTkButton(
            self.sidebar,
            text="🧹 Clean All Dismissed",
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            command=self.on_clean_dismissed
        )
        self.btn_clean_dismissed.grid(row=13, column=0, padx=20, pady=(0, 15), sticky="ew")

        # Bottom theme toggle
        theme_lbl = ctk.CTkLabel(self.sidebar, text="Appearance Mode:", font=ctk.CTkFont(size=11))
        theme_lbl.grid(row=15, column=0, padx=20, pady=(10, 0), sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=["Dark", "Light", "System"],
            command=ctk.set_appearance_mode
        )
        self.theme_menu.grid(row=16, column=0, padx=20, pady=(2, 20), sticky="ew")

    def _build_main_view(self):
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=3) # Leads list
        self.main_container.grid_rowconfigure(3, weight=1) # Log Console

        # Top Bar: Connection & Metrics Cards
        self.top_bar = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.top_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total = self._create_metric_card(self.top_bar, 0, "Total In Inbox", "0", "#34495e")
        self.card_new = self._create_metric_card(self.top_bar, 1, "New Awaiting Review", "0", "#2980b9")
        self.card_approved = self._create_metric_card(self.top_bar, 2, "Approved Leads", "0", "#27ae60")
        self.card_dismissed = self._create_metric_card(self.top_bar, 3, "Dismissed Leads", "0", "#c0392b")

        # Filter & Search Controls Bar
        self.controls_bar = ctk.CTkFrame(self.main_container)
        self.controls_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=2)
        self.controls_bar.grid_columnconfigure(1, weight=1)

        # Tab Segmented Button
        self.tab_filter = ctk.CTkSegmentedButton(
            self.controls_bar,
            values=["New", "Approved", "Dismissed", "All"],
            command=self.on_filter_changed
        )
        self.tab_filter.set("New")
        self.tab_filter.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        # Quick Search Box
        self.search_entry = ctk.CTkEntry(
            self.controls_bar,
            placeholder_text="🔍 Filter by company, title, or location...",
            height=32
        )
        self.search_entry.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.render_leads_list())

        # Leads Scrollable Area
        self.leads_scroll = ctk.CTkScrollableFrame(self.main_container, label_text="Discovered Job Postings")
        self.leads_scroll.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self.leads_scroll.grid_columnconfigure(0, weight=1)

        # Bottom Live Activity Console
        self.console_frame = ctk.CTkFrame(self.main_container)
        self.console_frame.grid(row=3, column=0, sticky="nsew")
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

    # --- Data Operations ---

    def refresh_leads(self):
        if self.is_loading:
            return
        self.is_loading = True
        self.btn_refresh.configure(state="disabled", text="⏳ Loading...")
        self.log(f"🔄 Fetching leads from Notion ({get_discovery_db_id()[:8]}...)\n")

        def _worker():
            try:
                # Fetch all for metrics, then filter
                all_leads = fetch_discovered_leads(status_filter="all")
                self.after(0, lambda: self._on_leads_loaded(all_leads))
            except Exception as e:
                self.after(0, lambda: self._on_leads_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_leads_loaded(self, leads: List[Dict]):
        self.leads = leads
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh Leads")

        # Update metrics
        total = len(leads)
        new_cnt = sum(1 for l in leads if l["status"].lower() == "new")
        app_cnt = sum(1 for l in leads if l["status"].lower() == "approved")
        dis_cnt = sum(1 for l in leads if l["status"].lower() == "dismissed")

        self.card_total.configure(text=str(total))
        self.card_new.configure(text=str(new_cnt))
        self.card_approved.configure(text=str(app_cnt))
        self.card_dismissed.configure(text=str(dis_cnt))

        self.log(f"✅ Loaded {total} total leads ({new_cnt} New, {app_cnt} Approved, {dis_cnt} Dismissed).\n")
        self.render_leads_list()

    def _on_leads_error(self, err_msg: str):
        self.is_loading = False
        self.btn_refresh.configure(state="normal", text="🔄 Refresh Leads")
        self.log(f"❌ Error fetching leads: {err_msg}\n")
        messagebox.showerror("Notion API Error", f"Failed to retrieve leads from Notion:\n\n{err_msg}")

    def on_filter_changed(self, value):
        self.current_filter = value
        self.render_leads_list()

    def render_leads_list(self):
        # Clear existing cards
        for widget in self.leads_scroll.winfo_children():
            widget.destroy()

        search_query = self.search_entry.get().strip().lower()

        filtered = []
        for l in self.leads:
            # Status filter
            if self.current_filter != "All" and l["status"].lower() != self.current_filter.lower():
                continue
            # Search query
            if search_query:
                combined_txt = f"{l['company']} {l['role']} {l['location']} {l['notes']}".lower()
                if search_query not in combined_txt:
                    continue
            filtered.append(l)

        if not filtered:
            empty_lbl = ctk.CTkLabel(
                self.leads_scroll,
                text=f"No postings found matching '{self.current_filter}' status.",
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            return

        for lead in filtered:
            self._create_lead_card(lead)

    def _create_lead_card(self, lead: Dict):
        card = ctk.CTkFrame(self.leads_scroll, fg_color="#2b2b36", corner_radius=8)
        card.pack(fill="x", padx=4, pady=5)
        card.grid_columnconfigure(0, weight=1)

        # Header Row: Company, Location badge, Score badge, Status badge
        header_frame = ctk.CTkFrame(card, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        header_frame.grid_columnconfigure(0, weight=1)

        company_lbl = ctk.CTkLabel(
            header_frame,
            text=lead["company"],
            font=ctk.CTkFont(size=15, weight="bold")
        )
        company_lbl.grid(row=0, column=0, sticky="w")

        # Badges frame on right
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
        score_val = lead["score"]
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

        # Role Title
        role_lbl = ctk.CTkLabel(
            card,
            text=lead["role"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ecf0f1"
        )
        role_lbl.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))

        # Notes / Snippet Preview
        snippet = lead["notes"]
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

        # Action Buttons Row
        actions_frame = ctk.CTkFrame(card, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

        # Left: Web Link
        if lead["url"]:
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

        # Right Action Buttons
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

    # --- Action Handlers ---

    def on_update_status(self, page_id: str, new_status: str, company: str):
        self.log(f"🔄 Updating '{company}' status to {new_status}...\n")
        def _worker():
            try:
                update_lead_status(page_id, new_status)
                self.log(f"✅ Lead '{company}' marked as {new_status}.\n")
                # Update local memory
                for l in self.leads:
                    if l["id"] == page_id:
                        l["status"] = new_status
                        break
                self.after(0, self.render_leads_list)
                self.after(0, self._recount_metrics)
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
                self.leads = [l for l in self.leads if l["id"] != page_id]
                self.after(0, self.render_leads_list)
                self.after(0, self._recount_metrics)
            except Exception as e:
                self.log(f"❌ Failed to delete lead: {str(e)}\n")
        threading.Thread(target=_worker, daemon=True).start()

    def _recount_metrics(self):
        total = len(self.leads)
        new_cnt = sum(1 for l in self.leads if l["status"].lower() == "new")
        app_cnt = sum(1 for l in self.leads if l["status"].lower() == "approved")
        dis_cnt = sum(1 for l in self.leads if l["status"].lower() == "dismissed")
        self.card_total.configure(text=str(total))
        self.card_new.configure(text=str(new_cnt))
        self.card_approved.configure(text=str(app_cnt))
        self.card_dismissed.configure(text=str(dis_cnt))

    def on_clean_dismissed(self):
        dismissed_count = sum(1 for l in self.leads if l["status"].lower() == "dismissed")
        if dismissed_count == 0:
            messagebox.showinfo("Nothing to Clean", "There are no dismissed leads in your inbox!")
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

        self.btn_run_scout.configure(state="disabled", text="⏳ Running Scout...")
        self.btn_stop_scout.configure(state="normal", fg_color="#c0392b")
        self.scout_stop_event.clear()

        self.log(f"\n{'='*55}\n🚀 Launching Job Scout (Freshness: {freshness}, Category: {category})\n{'='*55}\n")

        def _worker():
            try:
                run_scout_process(
                    freshness=freshness,
                    category=category,
                    log_callback=self.log,
                    stop_event=self.scout_stop_event
                )
            except Exception as e:
                self.log(f"❌ Scout execution error: {str(e)}\n")
            finally:
                self.after(0, self._on_scout_finished)

        self.scout_thread = threading.Thread(target=_worker, daemon=True)
        self.scout_thread.start()

    def on_stop_scout(self):
        self.scout_stop_event.set()
        self.log("🛑 Stop signal sent to Job Scout...\n")
        self.btn_stop_scout.configure(state="disabled", fg_color="#7f8c8d")

    def _on_scout_finished(self):
        self.btn_run_scout.configure(state="normal", text="🚀 Run Job Scout")
        self.btn_stop_scout.configure(state="disabled", fg_color="#7f8c8d")
        self.log("🔄 Triggering automatic inbox refresh...\n")
        self.refresh_leads()

if __name__ == "__main__":
    app = CareerDashboardApp()
    app.mainloop()
