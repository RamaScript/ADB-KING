"""
ui.py
Full Tkinter UI for ADB Device Manager.

IMPROVEMENTS OVER ORIGINAL:
- ADB check runs in a background thread — UI never freezes on startup
- _refresh_devices / _refresh_apps use a busy-guard (_busy flag) to prevent
  concurrent background threads stomping each other
- _clear_tree uses tree.delete(*children) bulk call instead of one-by-one loop
- Search is debounced: only runs _apply_filter_and_search() 250 ms after the
  user stops typing — no tree thrash on every keystroke
- Device info loads in parallel with app list (two threads, not serialised)
- _get_serial() is more robust: handles combo labels with/without status suffix
- adb_start_server() called once on startup to warm the ADB daemon
- Combo auto-selects first device but guards against re-triggering load when
  the device is already selected
- _on_device_selected no longer called from _refresh_devices to avoid double-load
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import os
from datetime import datetime

import adb_manager
import app_manager


# ── Colour palette ─────────────────────────────────────────────────────────────
BG_DARK        = "#1a1d23"
BG_CARD        = "#22262f"
BG_PANEL       = "#1e2129"
BG_TABLE       = "#181b22"
ACCENT         = "#4f8ef7"
ACCENT_HOVER   = "#6aa3ff"
DANGER         = "#e05c5c"
SUCCESS        = "#4caf7d"
WARNING        = "#f0a830"
TEXT_PRIMARY   = "#e8eaf0"
TEXT_SECONDARY = "#8a8fa8"
TEXT_DISABLED  = "#4a4f65"
BORDER         = "#2d3245"
ROW_ODD        = "#1e2230"
ROW_EVEN       = "#1a1d28"
ROW_SELECT     = "#2a3a5c"


class ADBDeviceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB Device Manager")
        self.root.geometry("1100x760")
        self.root.minsize(900, 620)
        self.root.configure(bg=BG_DARK)

        # ── State ──────────────────────────────────────────────────────────────
        self.devices            = []
        self.selected_serial    = tk.StringVar()
        self.search_var         = tk.StringVar()
        self.current_filter     = "all"
        self.all_packages       = []
        self.visible_packages   = []

        # Guard: prevents two background refreshes running at the same time.
        self._busy              = False
        # After-ID for debounced search
        self._search_after_id   = None
        # Track the serial that was last fully loaded so we don't reload when
        # the user clicks the same device in the combo twice.
        self._loaded_serial     = None

        self._setup_styles()
        self._build_ui()

        # Start the ADB daemon warm-up and device scan in the background so
        # the window appears immediately without any freeze.
        self.run_in_thread(adb_manager.adb_start_server)
        self.root.after(50, self._check_adb_and_load)   # tiny delay lets window render first

    # ── Style setup ────────────────────────────────────────────────────────────
    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=BG_DARK, foreground=TEXT_PRIMARY,
                         font=("Segoe UI", 10), borderwidth=0)
        style.configure("TFrame",       background=BG_DARK)
        style.configure("Card.TFrame",  background=BG_CARD)
        style.configure("Panel.TFrame", background=BG_PANEL)

        style.configure("TLabel",                background=BG_DARK,  foreground=TEXT_PRIMARY)
        style.configure("Card.TLabel",           background=BG_CARD,  foreground=TEXT_PRIMARY)
        style.configure("Secondary.TLabel",      background=BG_DARK,  foreground=TEXT_SECONDARY, font=("Segoe UI", 9))
        style.configure("Card.Secondary.TLabel", background=BG_CARD,  foreground=TEXT_SECONDARY, font=("Segoe UI", 9))
        style.configure("Title.TLabel",          background=BG_DARK,  foreground=TEXT_PRIMARY,   font=("Segoe UI", 14, "bold"))
        style.configure("Accent.TLabel",         background=BG_DARK,  foreground=ACCENT,         font=("Segoe UI", 10, "bold"))

        style.configure("TButton", background=BG_CARD, foreground=TEXT_PRIMARY,
                         font=("Segoe UI", 9), borderwidth=1, relief="flat", padding=(10, 5))
        style.map("TButton",
                  background=[("active", BORDER), ("disabled", BG_PANEL)],
                  foreground=[("disabled", TEXT_DISABLED)])

        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"), padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("active", ACCENT_HOVER), ("disabled", TEXT_DISABLED)])

        style.configure("Danger.TButton", background=DANGER, foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"), padding=(10, 5))
        style.map("Danger.TButton",
                  background=[("active", "#c74c4c"), ("disabled", TEXT_DISABLED)])

        style.configure("Success.TButton", background=SUCCESS, foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"), padding=(10, 5))
        style.map("Success.TButton",
                  background=[("active", "#3d9a68"), ("disabled", TEXT_DISABLED)])

        style.configure("Filter.TButton", background=BG_PANEL, foreground=TEXT_SECONDARY,
                         font=("Segoe UI", 9), padding=(10, 4))
        style.map("Filter.TButton",
                  background=[("active", BG_CARD)],
                  foreground=[("active", TEXT_PRIMARY)])

        style.configure("FilterActive.TButton", background=ACCENT, foreground="#ffffff",
                         font=("Segoe UI", 9, "bold"), padding=(10, 4))

        style.configure("TCombobox", fieldbackground=BG_CARD, background=BG_CARD,
                         foreground=TEXT_PRIMARY, selectbackground=ACCENT, selectforeground="#ffffff")
        style.map("TCombobox", fieldbackground=[("readonly", BG_CARD)])

        style.configure("TEntry", fieldbackground=BG_CARD, foreground=TEXT_PRIMARY,
                         insertcolor=TEXT_PRIMARY, borderwidth=1)

        style.configure("Treeview",
                         background=BG_TABLE, foreground=TEXT_PRIMARY,
                         fieldbackground=BG_TABLE, rowheight=26,
                         font=("Segoe UI", 9), borderwidth=0)
        style.configure("Treeview.Heading",
                         background=BG_PANEL, foreground=TEXT_SECONDARY,
                         font=("Segoe UI", 9, "bold"), relief="flat", borderwidth=0)
        style.map("Treeview",
                  background=[("selected", ROW_SELECT)],
                  foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading",
                  background=[("active", BG_CARD)])

        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_SECONDARY,
                         font=("Segoe UI", 10), padding=(14, 6))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_CARD)],
                  foreground=[("selected", TEXT_PRIMARY)])

        style.configure("Vertical.TScrollbar",   background=BG_CARD, troughcolor=BG_DARK, borderwidth=0, arrowsize=12)
        style.configure("Horizontal.TScrollbar", background=BG_CARD, troughcolor=BG_DARK, borderwidth=0, arrowsize=12)
        style.configure("TSeparator",   background=BORDER)
        style.configure("TProgressbar", background=ACCENT, troughcolor=BG_PANEL, borderwidth=0, thickness=3)

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        outer = ttk.Frame(self.root, style="TFrame", padding=0)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._build_header(outer)

        self.notebook = ttk.Notebook(outer)
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self._build_apps_tab()
        self._build_commands_tab()

        self._build_output_panel(outer)
        self._build_statusbar(outer)

    def _build_header(self, parent):
        header = tk.Frame(parent, bg=BG_CARD, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(2, weight=1)

        tk.Label(header, text="⬛ ADB Device Manager", bg=BG_CARD,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 14, "bold")).grid(
            row=0, column=0, padx=18, pady=18, sticky="w")

        tk.Frame(header, bg=BORDER, width=1).grid(row=0, column=1, sticky="ns", pady=10)

        dev_frame = tk.Frame(header, bg=BG_CARD)
        dev_frame.grid(row=0, column=2, padx=16, sticky="w")

        tk.Label(dev_frame, text="Device:", bg=BG_CARD, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 6))

        self.device_combo = ttk.Combobox(dev_frame, textvariable=self.selected_serial,
                                          state="readonly", width=38, font=("Segoe UI", 9))
        self.device_combo.grid(row=0, column=1, padx=(0, 8))
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)

        self.refresh_devices_btn = ttk.Button(dev_frame, text="⟳ Refresh Devices",
                                               command=self._refresh_devices)
        self.refresh_devices_btn.grid(row=0, column=2, padx=(0, 8))

        self.device_status_label = tk.Label(dev_frame, text="No device selected",
                                             bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 9))
        self.device_status_label.grid(row=0, column=3, padx=(4, 0))

    def _build_apps_tab(self):
        tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab, text="  📱  Apps  ")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        top = tk.Frame(tab, bg=BG_DARK)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        self._build_device_info_card(top)
        self._build_filter_search(top)

        mid = tk.Frame(tab, bg=BG_DARK)
        mid.grid(row=1, column=0, sticky="nsew")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        self._build_package_table(mid)
        self._build_action_panel(mid)

    def _build_device_info_card(self, parent):
        card = tk.Frame(parent, bg=BG_CARD, padx=16, pady=12)
        card.grid(row=0, column=0, sticky="ns", padx=(10, 6), pady=(10, 0))

        tk.Label(card, text="DEVICE INFO", bg=BG_CARD, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.info_labels = {}
        fields = [
            ("Manufacturer", "manufacturer"),
            ("Model",        "model"),
            ("Android",      "android_version"),
            ("SDK",          "sdk"),
            ("Serial",       "serial"),
        ]
        for i, (label, key) in enumerate(fields):
            tk.Label(card, text=f"{label}:", bg=BG_CARD, fg=TEXT_SECONDARY,
                     font=("Segoe UI", 9), width=12, anchor="w").grid(row=i+1, column=0, sticky="w", pady=1)
            lbl = tk.Label(card, text="—", bg=BG_CARD, fg=TEXT_PRIMARY,
                           font=("Segoe UI", 9), anchor="w", width=22)
            lbl.grid(row=i+1, column=1, sticky="w", padx=(4, 0), pady=1)
            self.info_labels[key] = lbl

        tk.Label(card, text="Build:", bg=BG_CARD, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9), width=12, anchor="w").grid(
            row=len(fields)+1, column=0, sticky="w", pady=1)
        self.fingerprint_label = tk.Label(card, text="—", bg=BG_CARD, fg=TEXT_SECONDARY,
                                           font=("Segoe UI", 8), anchor="w", width=22,
                                           wraplength=160, justify="left")
        self.fingerprint_label.grid(row=len(fields)+1, column=1, sticky="w", padx=(4, 0), pady=1)

    def _build_filter_search(self, parent):
        right = tk.Frame(parent, bg=BG_DARK)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(10, 0))
        right.grid_columnconfigure(0, weight=1)

        filter_frame = tk.Frame(right, bg=BG_DARK)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.filter_buttons = {}
        for i, (key, label) in enumerate([
            ("all",     "All Apps"),
            ("user",    "User Apps"),
            ("system",  "System Apps"),
            ("enabled", "Enabled"),
            ("disabled","Disabled"),
        ]):
            btn = ttk.Button(filter_frame, text=label, command=lambda k=key: self._set_filter(k))
            btn.grid(row=0, column=i, padx=(0, 4))
            self.filter_buttons[key] = btn
        self._update_filter_button_styles()

        search_frame = tk.Frame(right, bg=BG_DARK)
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        search_entry.grid(row=0, column=0, sticky="ew", ipady=4)
        search_entry.insert(0, "🔍  Search packages...")
        search_entry.bind("<FocusIn>",  self._search_focus_in)
        search_entry.bind("<FocusOut>", self._search_focus_out)
        self.search_entry = search_entry
        self.search_placeholder_active = True
        # trace fires _on_search_changed which debounces before doing real work
        self.search_var.trace_add("write", self._on_search_changed)

        ttk.Button(search_frame, text="✕", width=3,
                   command=self._clear_search).grid(row=0, column=1, padx=(4, 0))
        ttk.Button(search_frame, text="⟳ Refresh Apps",
                   command=self._refresh_apps).grid(row=0, column=2, padx=(8, 0))

        export_frame = tk.Frame(right, bg=BG_DARK)
        export_frame.grid(row=2, column=0, sticky="w", pady=(6, 0))
        tk.Label(export_frame, text="Export:", bg=BG_DARK, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(export_frame, text="📄 TXT", command=self._export_txt).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(export_frame, text="📊 CSV", command=self._export_csv).grid(row=0, column=2)

        self.pkg_count_label = tk.Label(right, text="", bg=BG_DARK, fg=TEXT_SECONDARY, font=("Segoe UI", 9))
        self.pkg_count_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

    def _build_package_table(self, parent):
        table_frame = tk.Frame(parent, bg=BG_TABLE)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 4), pady=(6, 10))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        cols = ("Package Name", "Type", "Status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("Package Name", text="Package Name", command=lambda: self._sort_tree("Package Name"))
        self.tree.heading("Type",         text="Type",         command=lambda: self._sort_tree("Type"))
        self.tree.heading("Status",       text="Status",       command=lambda: self._sort_tree("Status"))

        self.tree.column("Package Name", width=480, minwidth=200, stretch=True)
        self.tree.column("Type",         width=100, minwidth=80,  stretch=False, anchor="center")
        self.tree.column("Status",       width=110, minwidth=80,  stretch=False, anchor="center")

        self.tree.tag_configure("odd",      background=ROW_ODD)
        self.tree.tag_configure("even",     background=ROW_EVEN)
        self.tree.tag_configure("disabled", foreground=TEXT_DISABLED)
        self.tree.tag_configure("system",   foreground=WARNING)
        self.tree.tag_configure("user",     foreground="#b0e8c8")

        vsb = ttk.Scrollbar(table_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_package_selected)
        self.tree.bind("<Double-1>",         self._on_package_double_click)

        self._sort_col     = None
        self._sort_reverse = False

    def _build_action_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_CARD, padx=10, pady=10, width=170)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(6, 10))
        panel.grid_propagate(False)

        tk.Label(panel, text="ACTIONS", bg=BG_CARD, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 10))

        self.selected_pkg_label = tk.Label(panel, text="No package selected",
                                            bg=BG_CARD, fg=TEXT_SECONDARY,
                                            font=("Segoe UI", 8), wraplength=145, justify="left")
        self.selected_pkg_label.pack(anchor="w", pady=(0, 10))

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=(0, 10))

        self.action_buttons = {}
        for key, label, style, cmd in [
            ("enable",    "✅  Enable App",       "Success.TButton", self._action_enable),
            ("disable",   "🚫  Disable App",       "Danger.TButton",  self._action_disable),
            ("uninstall", "🗑  Uninstall (User)",  "Danger.TButton",  self._action_uninstall),
            ("appinfo",   "ℹ  Open App Info",     "TButton",          self._action_open_info),
            ("copy",      "📋  Copy Package Name", "TButton",          self._action_copy),
        ]:
            btn = ttk.Button(panel, text=label, style=style, command=cmd, state="disabled")
            btn.pack(fill="x", pady=(0, 6))
            self.action_buttons[key] = btn

    def _build_commands_tab(self):
        tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(tab, text="  ⌨️  Commands  ")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        top = tk.Frame(tab, bg=BG_CARD, padx=18, pady=16)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(12, 6))
        top.grid_columnconfigure(1, weight=1)

        tk.Label(top, text="Custom ADB Shell Command", bg=BG_CARD,
                 fg=TEXT_PRIMARY, font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        tk.Label(top, text="Command:", bg=BG_CARD, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=(0, 8))

        self.custom_cmd_var = tk.StringVar()
        cmd_entry = ttk.Entry(top, textvariable=self.custom_cmd_var,
                               font=("Segoe UI Mono", 10), width=60)
        cmd_entry.grid(row=1, column=1, sticky="ew", ipady=5)
        cmd_entry.insert(0, "pm list packages")
        cmd_entry.bind("<Return>", lambda e: self._run_custom_command())

        ttk.Button(top, text="▶  Run Shell Command", style="Accent.TButton",
                   command=self._run_custom_command).grid(row=1, column=2, padx=(8, 0))

        tk.Label(top, text="Runs as: adb -s <device> shell <command>",
                 bg=BG_CARD, fg=TEXT_SECONDARY, font=("Segoe UI", 9)).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0))

        note = tk.Frame(tab, bg=BG_PANEL, padx=14, pady=10)
        note.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 6))
        tk.Label(note, text="⚠️  Advanced Feature", bg=BG_PANEL, fg=WARNING,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(note,
                 text="This section is for advanced users. Commands run directly on the device.\n"
                      "Be careful with destructive commands. Output appears in the Command Output panel below.",
                 bg=BG_PANEL, fg=TEXT_SECONDARY, font=("Segoe UI", 9),
                 justify="left", wraplength=700).pack(anchor="w", pady=(6, 0))

    def _build_output_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL)
        panel.grid(row=2, column=0, sticky="ew")

        header = tk.Frame(panel, bg=BG_PANEL)
        header.pack(fill="x", padx=10, pady=(6, 2))
        tk.Label(header, text="Command Output", bg=BG_PANEL, fg=TEXT_SECONDARY,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(header, text="Clear", command=self._clear_output).pack(side="right")

        output_frame = tk.Frame(panel, bg=BG_PANEL)
        output_frame.pack(fill="both", padx=10, pady=(0, 6))

        self.output_text = tk.Text(output_frame, height=7, bg="#0e1018",
                                    fg=TEXT_PRIMARY, font=("Consolas", 9),
                                    wrap="word", state="disabled",
                                    relief="flat", borderwidth=0,
                                    insertbackground=TEXT_PRIMARY)
        self.output_text.tag_configure("header",  foreground=ACCENT,          font=("Consolas", 9, "bold"))
        self.output_text.tag_configure("error",   foreground=DANGER)
        self.output_text.tag_configure("success", foreground=SUCCESS)
        self.output_text.tag_configure("warning", foreground=WARNING)
        self.output_text.tag_configure("muted",   foreground=TEXT_SECONDARY)

        vsb = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=vsb.set)
        self.output_text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _build_statusbar(self, parent):
        bar = tk.Frame(parent, bg=BG_CARD, height=26)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=1)

        self.status_label = tk.Label(bar, text="Ready", bg=BG_CARD,
                                      fg=TEXT_SECONDARY, font=("Segoe UI", 9), anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew", padx=12)

        self.progress = ttk.Progressbar(bar, mode="indeterminate",
                                         style="TProgressbar", length=120)
        self.progress.grid(row=0, column=1, padx=(0, 12), pady=3)
        self._set_progress(False)

    # ── Utilities ──────────────────────────────────────────────────────────────
    def _set_status(self, msg, color=None):
        self.status_label.configure(text=msg, fg=color or TEXT_SECONDARY)

    def _set_progress(self, active):
        if active:
            self.progress.start(10)
        else:
            self.progress.stop()

    def run_in_thread(self, task_fn, callback_fn=None):
        """Run task_fn in a daemon thread; deliver result to main thread via after()."""
        def _worker():
            result = task_fn()
            if callback_fn:
                self.root.after(0, lambda: callback_fn(result))
        threading.Thread(target=_worker, daemon=True).start()

    def _append_output(self, text, tag=""):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text, tag)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _log_command(self, cmd_parts, stdout, stderr, code, ts):
        self._append_output(f"\n[{ts}] ", "muted")
        self._append_output(" ".join(cmd_parts) + "\n", "header")
        if stdout:
            self._append_output(stdout + "\n", "success" if code == 0 else "")
        if stderr:
            self._append_output(stderr + "\n", "error")
        self._append_output(f"Exit code: {code}\n", "success" if code == 0 else "error")

    def _get_serial(self):
        """Return the raw serial from the combo (strips the ' [status]' suffix)."""
        v = self.selected_serial.get().strip()
        if not v:
            return None
        # combo values are formatted as "SERIAL   [status]"
        return v.split("   ")[0].strip()

    # ── ADB check + device loading ─────────────────────────────────────────────
    def _check_adb_and_load(self):
        """Run ADB version check in background so UI stays responsive."""
        def task():
            adb = adb_manager.get_adb_path()
            if not adb:
                return None, None
            stdout, _, code, _ = adb_manager.run_adb_command(["version"])
            return adb, stdout.splitlines()[0] if stdout else "Unknown version"

        def callback(result):
            adb, version_line = result
            if not adb:
                messagebox.showerror(
                    "ADB Not Found",
                    "ADB not found.\n\nPlease install Android Platform Tools or place "
                    "the adb executable inside the project folder.\n\n"
                    "Download: https://developer.android.com/studio/releases/platform-tools"
                )
                self._set_status("ADB not found. Install Android Platform Tools.", DANGER)
                return
            self._append_output(f"ADB detected: {version_line}\n", "success")
            self._set_status(f"ADB ready: {version_line}")
            self._refresh_devices()

        self.run_in_thread(task, callback)

    def _refresh_devices(self):
        """Scan for connected devices. Guarded against concurrent calls."""
        if self._busy:
            return
        self._busy = True
        self._set_status("Scanning for devices…")
        self._set_progress(True)
        self.refresh_devices_btn.configure(state="disabled")

        def task():
            return adb_manager.list_devices()

        def callback(result):
            self._busy = False
            self._set_progress(False)
            self.refresh_devices_btn.configure(state="normal")

            devices, err = result
            self.devices = devices

            combo_values = [f"{d['serial']}   [{d['status']}]" for d in devices]
            self.device_combo["values"] = combo_values

            if not devices:
                self.selected_serial.set("")
                self.device_combo.set("")
                self._set_status(
                    "No Android device connected. Connect phone with USB and enable USB debugging.",
                    WARNING
                )
                self.device_status_label.configure(text="No device connected", fg=WARNING)
                if err:
                    self._append_output(f"Error: {err}\n", "error")
                return

            # If the currently selected serial is still in the list, keep it.
            cur_serial = self._get_serial()
            match_idx  = next((i for i, d in enumerate(devices) if d["serial"] == cur_serial), None)

            if match_idx is not None:
                # Same device is still there — don't reload apps.
                self.device_combo.current(match_idx)
                self._set_status(f"Device still connected: {cur_serial}", SUCCESS)
            else:
                # New device list — select the first entry and load it.
                self.device_combo.current(0)
                self._loaded_serial = None   # force a fresh load
                self._on_device_selected(None)

        self.run_in_thread(task, callback)

    def _on_device_selected(self, event):
        serial = self._get_serial()
        if not serial:
            return

        # Find the device's status in our cached list
        status = next((d["status"] for d in self.devices if d["serial"] == serial), "unknown")

        if status == "unauthorized":
            self.device_status_label.configure(text="⚠ Unauthorized", fg=WARNING)
            messagebox.showwarning(
                "Unauthorized Device",
                "Device unauthorized.\nPlease allow the USB debugging popup on your phone."
            )
            return

        if status == "offline":
            self.device_status_label.configure(text="⚠ Offline", fg=DANGER)
            self._set_status("Device is offline.", DANGER)
            return

        if status != "device":
            self.device_status_label.configure(text=f"⚠ {status}", fg=WARNING)
            return

        self.device_status_label.configure(text="● Connected", fg=SUCCESS)

        # Avoid redundant reloads if the user clicks the same device again
        if serial == self._loaded_serial:
            return
        self._loaded_serial = serial

        self._set_status(f"Loading device {serial}…")
        # Load device info and apps in parallel (two separate threads)
        self._load_device_info(serial)
        self._refresh_apps()

    def _load_device_info(self, serial):
        def task():
            return adb_manager.get_device_info(serial)

        def callback(info):
            for key, lbl in self.info_labels.items():
                lbl.configure(text=info.get(key, "—") or "—")
            fp = info.get("fingerprint", "—")
            display_fp = fp if len(fp) <= 40 else fp[:37] + "…"
            self.fingerprint_label.configure(text=display_fp)

        self.run_in_thread(task, callback)

    # ── Package loading + display ──────────────────────────────────────────────
    def _refresh_apps(self):
        serial = self._get_serial()
        if not serial:
            return
        if self._busy:
            self._set_status("Please wait — already loading…", WARNING)
            return

        self._busy = True
        self._set_status("Loading apps…")
        self._set_progress(True)
        self._clear_tree()
        self.pkg_count_label.configure(text="Loading…")

        def task():
            return app_manager.classify_packages(serial)

        def callback(result):
            self._busy = False
            self._set_progress(False)
            packages, err = result
            self.all_packages = packages
            if err:
                self._append_output(f"Warning during package load: {err}\n", "warning")
            self._apply_filter_and_search()
            self._set_status(f"Loaded {len(packages)} packages.")

        self.run_in_thread(task, callback)

    def _apply_filter_and_search(self):
        search = "" if self.search_placeholder_active else self.search_var.get().lower()
        filt   = self.current_filter

        result = [
            pkg for pkg in self.all_packages
            if (filt == "all"
                or (filt == "user"     and pkg["type"]   == "User")
                or (filt == "system"   and pkg["type"]   == "System")
                or (filt == "enabled"  and pkg["status"] == "Enabled")
                or (filt == "disabled" and pkg["status"] == "Disabled"))
            and (not search or search in pkg["package"].lower())
        ]

        self.visible_packages = result
        self._populate_tree(result)
        self.pkg_count_label.configure(text=f"{len(result)} packages shown")

    def _populate_tree(self, packages):
        """Clear tree with a single bulk delete, then re-insert all rows."""
        self._clear_tree()
        insert = self.tree.insert          # local ref for speed in tight loop
        for i, pkg in enumerate(packages):
            row_tag = "even" if i % 2 == 0 else "odd"
            if pkg["status"] == "Disabled":
                tags = (row_tag, "disabled")
            elif pkg["type"] == "System":
                tags = (row_tag, "system")
            elif pkg["type"] == "User":
                tags = (row_tag, "user")
            else:
                tags = (row_tag,)
            insert("", "end", values=(pkg["package"], pkg["type"], pkg["status"]), tags=tags)

    def _clear_tree(self):
        """Bulk-delete all tree rows in one call — much faster than one-by-one."""
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

    def _sort_tree(self, col):
        col_map = {"Package Name": "package", "Type": "type", "Status": "status"}
        key = col_map[col]
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col    = col
            self._sort_reverse = False
        self.visible_packages.sort(key=lambda p: p[key].lower(), reverse=self._sort_reverse)
        self._populate_tree(self.visible_packages)

    # ── Filter / search ────────────────────────────────────────────────────────
    def _set_filter(self, key):
        self.current_filter = key
        self._update_filter_button_styles()
        self._apply_filter_and_search()

    def _update_filter_button_styles(self):
        for key, btn in self.filter_buttons.items():
            btn.configure(style="FilterActive.TButton" if key == self.current_filter else "Filter.TButton")

    def _search_focus_in(self, event):
        if self.search_placeholder_active:
            self.search_entry.delete(0, "end")
            self.search_entry.configure(foreground=TEXT_PRIMARY)
            self.search_placeholder_active = False

    def _search_focus_out(self, event):
        if not self.search_var.get():
            self.search_entry.insert(0, "🔍  Search packages...")
            self.search_entry.configure(foreground=TEXT_SECONDARY)
            self.search_placeholder_active = True

    def _on_search_changed(self, *_):
        """Debounce: wait 250 ms after the user stops typing before filtering."""
        if self.search_placeholder_active:
            return
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(250, self._apply_filter_and_search)

    def _clear_search(self):
        self.search_var.set("")
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "🔍  Search packages...")
        self.search_entry.configure(foreground=TEXT_SECONDARY)
        self.search_placeholder_active = True
        self._apply_filter_and_search()

    # ── Package selection ──────────────────────────────────────────────────────
    def _on_package_selected(self, event):
        sel = self.tree.selection()
        if sel:
            pkg_name = self.tree.item(sel[0], "values")[0]
            self.selected_pkg_label.configure(text=pkg_name, fg=TEXT_PRIMARY)
            for btn in self.action_buttons.values():
                btn.configure(state="normal")
        else:
            self.selected_pkg_label.configure(text="No package selected", fg=TEXT_SECONDARY)
            for btn in self.action_buttons.values():
                btn.configure(state="disabled")

    def _on_package_double_click(self, event):
        self._action_open_info()

    def _get_selected_package(self):
        sel = self.tree.selection()
        if not sel:
            return None, None, None
        v = self.tree.item(sel[0], "values")
        return v[0], v[1], v[2]

    # ── Actions ────────────────────────────────────────────────────────────────
    def _action_enable(self):
        serial = self._get_serial()
        pkg, ptype, status = self._get_selected_package()
        if not pkg or not serial:
            return
        if not messagebox.askyesno("Confirm Enable", f"Enable package?\n\n{pkg}"):
            return
        self._set_status(f"Enabling {pkg}…")
        self._set_progress(True)

        def task():
            return app_manager.enable_package(serial, pkg)

        def callback(r):
            stdout, stderr, code, ts = r
            self._set_progress(False)
            self._log_command([f"adb -s {serial} shell pm enable {pkg}"], stdout, stderr, code, ts)
            self._set_status("Done.", SUCCESS if code == 0 else DANGER)
            self._loaded_serial = None   # force fresh app list
            self._refresh_apps()

        self.run_in_thread(task, callback)

    def _action_disable(self):
        serial = self._get_serial()
        pkg, ptype, status = self._get_selected_package()
        if not pkg or not serial:
            return

        msg = (f"This is a SYSTEM app. Disabling it may break phone features.\n\nPackage: {pkg}\n\nContinue?"
               if ptype == "System" else f"Disable package?\n\n{pkg}")
        icon = "warning" if ptype == "System" else "question"
        title = "⚠ Disable System App" if ptype == "System" else "Confirm Disable"

        if not messagebox.askyesno(title, msg, icon=icon):
            return

        self._set_status(f"Disabling {pkg}…")
        self._set_progress(True)

        def task():
            return app_manager.disable_package(serial, pkg)

        def callback(r):
            stdout, stderr, code, ts = r
            self._set_progress(False)
            self._log_command([f"adb -s {serial} shell pm disable-user --user 0 {pkg}"], stdout, stderr, code, ts)
            self._set_status("Done.", SUCCESS if code == 0 else DANGER)
            self._loaded_serial = None
            self._refresh_apps()

        self.run_in_thread(task, callback)

    def _action_uninstall(self):
        serial = self._get_serial()
        pkg, ptype, status = self._get_selected_package()
        if not pkg or not serial:
            return

        msg = (f"This may remove a system app for the current user.\nIt may affect phone stability.\n\nPackage: {pkg}\n\nContinue?"
               if ptype == "System" else f"Uninstall for current user?\n\n{pkg}")
        icon = "warning" if ptype == "System" else "question"
        title = "⚠ Uninstall System App" if ptype == "System" else "Confirm Uninstall"

        if not messagebox.askyesno(title, msg, icon=icon):
            return

        self._set_status(f"Uninstalling {pkg}…")
        self._set_progress(True)

        def task():
            return app_manager.uninstall_package_for_user(serial, pkg)

        def callback(r):
            stdout, stderr, code, ts = r
            self._set_progress(False)
            self._log_command([f"adb -s {serial} shell pm uninstall --user 0 {pkg}"], stdout, stderr, code, ts)
            self._set_status("Done.", SUCCESS if code == 0 else DANGER)
            self._loaded_serial = None
            self._refresh_apps()

        self.run_in_thread(task, callback)

    def _action_open_info(self):
        serial = self._get_serial()
        pkg, _, _ = self._get_selected_package()
        if not pkg or not serial:
            return
        self._set_status(f"Opening app info for {pkg}…")
        self._set_progress(True)

        def task():
            return app_manager.open_app_info(serial, pkg)

        def callback(r):
            stdout, stderr, code, ts = r
            self._set_progress(False)
            self._log_command([f"adb -s {serial} shell am start ... {pkg}"], stdout, stderr, code, ts)
            self._set_status(
                "App info opened on device." if code == 0 else "Failed to open app info.",
                SUCCESS if code == 0 else DANGER
            )

        self.run_in_thread(task, callback)

    def _action_copy(self):
        pkg, _, _ = self._get_selected_package()
        if not pkg:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(pkg)
        self._set_status(f"Copied: {pkg}", SUCCESS)

    # ── Custom command ─────────────────────────────────────────────────────────
    def _run_custom_command(self):
        serial = self._get_serial()
        if not serial:
            messagebox.showwarning("No Device", "Please select a connected device first.")
            return
        cmd = self.custom_cmd_var.get().strip()
        if not cmd:
            messagebox.showwarning("Empty Command", "Please enter a shell command to run.")
            return

        self._set_status(f"Running: {cmd}…")
        self._set_progress(True)

        def task():
            return adb_manager.run_shell_command(serial, cmd)

        def callback(r):
            stdout, stderr, code, ts = r
            self._set_progress(False)
            self._log_command([f"adb -s {serial} shell {cmd}"], stdout, stderr, code, ts)
            self._set_status("Done.", SUCCESS if code == 0 else DANGER)

        self.run_in_thread(task, callback)

    # ── Export ─────────────────────────────────────────────────────────────────
    def _export_txt(self):
        if not self.visible_packages:
            messagebox.showinfo("Nothing to Export", "No packages to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Package List as TXT"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# ADB Device Manager — Package Export\n")
                f.write(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Device: {self._get_serial()}\n")
                f.write(f"# Filter: {self.current_filter} | Count: {len(self.visible_packages)}\n\n")
                for pkg in self.visible_packages:
                    f.write(f"{pkg['package']}  [{pkg['type']}]  [{pkg['status']}]\n")
            self._set_status(f"Exported {len(self.visible_packages)} packages to TXT.", SUCCESS)
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    def _export_csv(self):
        if not self.visible_packages:
            messagebox.showinfo("Nothing to Export", "No packages to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Package List as CSV"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["package_name", "type", "status"])
                for pkg in self.visible_packages:
                    writer.writerow([pkg["package"], pkg["type"], pkg["status"]])
            self._set_status(f"Exported {len(self.visible_packages)} packages to CSV.", SUCCESS)
        except Exception as e:
            messagebox.showerror("Export Error", str(e))