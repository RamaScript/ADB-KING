"""
ui.py  —  ADB Device Manager
Complete UI redesign: iOS 17 liquid glass / glassmorphism aesthetic.

Palette: airy blue-white background, frosted-glass cards, iOS system colors.
Logic layer is identical to the previous version — only the visual layer changed.
"""

import csv
import threading
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import adb_manager
import app_manager


# ── Design tokens ──────────────────────────────────────────────────────────────

# Background atmosphere
BG              = "#edf2fb"
BG_BLUR_1       = "#c7deff"
BG_BLUR_2       = "#cef4ea"
BG_BLUR_3       = "#e2d0ff"
BG_BLUR_4       = "#ffd6f0"

# Frosted glass surfaces
GLASS           = "#ffffff"
GLASS_2         = "#f4f8ff"
GLASS_3         = "#eef4ff"

# Terminal / dark surface
TERM_BG         = "#0d1117"
TERM_PANEL      = "#161b22"
TERM_BORDER     = "#30363d"
TERM_TEXT       = "#e6edf3"
TERM_MUTED      = "#7d8590"

# Borders
BORDER          = "#d8e6f8"
BORDER_2        = "#e8f0fa"

# iOS system colors
ACCENT          = "#0a84ff"
ACCENT_LIGHT    = "#e0f0ff"
ACCENT_DARK     = "#0060d0"
ACCENT_TEXT     = "#0050b8"

SUCCESS         = "#30d158"
SUCCESS_LIGHT   = "#dff6e7"
SUCCESS_TEXT    = "#1a7834"

WARNING         = "#ff9f0a"
WARNING_LIGHT   = "#fff4e0"
WARNING_TEXT    = "#7a4d00"

DANGER          = "#ff453a"
DANGER_LIGHT    = "#ffe8e7"
DANGER_TEXT     = "#9a1c18"

# Text hierarchy
T1              = "#1c1c1e"
T2              = "#3a3a3c"
T3              = "#636366"
T4              = "#8e8e93"
T5              = "#aeaeb2"

# Table rows
ROW_ODD         = "#ffffff"
ROW_EVEN        = "#f6f9ff"
ROW_SEL         = "#d8eaff"

FILTER_META = [
    ("all",      "All"),
    ("user",     "User"),
    ("system",   "System"),
    ("enabled",  "Enabled"),
    ("disabled", "Disabled"),
]


# ── Application ────────────────────────────────────────────────────────────────

class ADBDeviceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB Device Manager")
        self.root.geometry("1340x880")
        self.root.minsize(1100, 740)
        self.root.configure(bg=BG)
        self.root.option_add("*tearOff", False)

        self.devices              = []
        self.device_label_map     = {}
        self.selected_serial      = tk.StringVar()
        self.search_var           = tk.StringVar()
        self.custom_cmd_var       = tk.StringVar(value="pm list packages")
        self.current_filter       = "all"
        self.all_packages         = []
        self.visible_packages     = []
        self.selected_package_name= None
        self._search_placeholder  = True

        self._search_after_id     = None
        self._loaded_serial       = None
        self._sort_col            = None
        self._sort_reverse        = False
        self._active_jobs         = 0
        self._devices_loading     = False
        self._apps_loading        = False

        self._setup_fonts()
        self._setup_styles()
        self._build_ui()
        self._bind_shortcuts()
        self.root.bind("<Configure>", self._draw_bg)

        self._clear_device_info("Connect an Android phone with USB debugging enabled.")
        self._reset_package_browser("Checking ADB availability\u2026")
        self._update_selected_package_card(None)
        self._set_output_badge("Idle", TERM_PANEL, TERM_MUTED, "No commands run yet.")
        self._refresh_status_context()
        self._refresh_interactive_states()

        self.search_var.trace_add("write", self._on_search_changed)
        self.custom_cmd_var.trace_add("write", lambda *_: self._refresh_interactive_states())

        self.run_in_thread(adb_manager.adb_start_server)
        self.root.after(120, self._check_adb_and_load)

    # ── Fonts ──────────────────────────────────────────────────────────────────
    def _setup_fonts(self):
        available = set(tkfont.families())

        def pick(*names):
            for n in names:
                if n in available:
                    return n
            return "TkDefaultFont"

        sf   = pick("SF Pro Display", "SF Pro Text", "Helvetica Neue",
                    ".AppleSystemUIFont", "Segoe UI", "Arial")
        mono = pick("SF Mono", "Menlo", "JetBrains Mono", "Consolas", "Courier New")

        self.fonts = {
            "hero":      (sf, 22, "bold"),
            "title":     (sf, 16, "bold"),
            "heading":   (sf, 13, "bold"),
            "subhead":   (sf, 11),
            "body":      (sf, 10),
            "body_b":    (sf, 10, "bold"),
            "caption":   (sf, 9),
            "caption_b": (sf, 9, "bold"),
            "label":     (sf, 8, "bold"),
            "mono":      (mono, 10),
            "mono_sm":   (mono, 9),
        }

    # ── Styles ─────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")

        self.root.option_add("*TCombobox*Listbox*Background", GLASS)
        self.root.option_add("*TCombobox*Listbox*Foreground", T1)
        self.root.option_add("*TCombobox*Listbox*selectBackground", ACCENT_LIGHT)
        self.root.option_add("*TCombobox*Listbox*selectForeground", T1)

        s.configure(".", background=BG, foreground=T1, font=self.fonts["body"])
        s.configure("TFrame", background=BG)
        s.configure("TSeparator", background=BORDER)

        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=0)
        s.configure("TNotebook.Tab", background=GLASS_3, foreground=T3,
                    font=self.fonts["body"], padding=(20, 11), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", GLASS), ("active", GLASS_2)],
              foreground=[("selected", T1),    ("active", T2)])

        s.configure("Treeview",
                    background=GLASS, fieldbackground=GLASS, foreground=T1,
                    rowheight=36, font=self.fonts["caption"], borderwidth=0, relief="flat")
        s.configure("Treeview.Heading",
                    background=GLASS_3, foreground=T3, font=self.fonts["caption_b"],
                    borderwidth=0, relief="flat", padding=(14, 10))
        s.map("Treeview",
              background=[("selected", ROW_SEL)],
              foreground=[("selected", T1)])
        s.map("Treeview.Heading",
              background=[("active", GLASS_2)],
              foreground=[("active", T2)])

        s.configure("Vertical.TScrollbar",
                    troughcolor=GLASS_2, background=BORDER,
                    borderwidth=0, arrowsize=10, width=8)
        s.configure("Horizontal.TScrollbar",
                    troughcolor=GLASS_2, background=BORDER,
                    borderwidth=0, arrowsize=10, width=8)

        s.configure("TProgressbar",
                    background=ACCENT, troughcolor=ACCENT_LIGHT,
                    borderwidth=0, thickness=3)

        s.configure("Glass.TEntry",
                    fieldbackground=GLASS, foreground=T1,
                    bordercolor=BORDER, lightcolor=GLASS, darkcolor=GLASS,
                    insertcolor=T1, padding=10)
        s.configure("Glass.TCombobox",
                    fieldbackground=GLASS, background=GLASS, foreground=T1,
                    bordercolor=BORDER, lightcolor=GLASS, darkcolor=GLASS,
                    arrowcolor=T3, selectbackground=ACCENT_LIGHT, selectforeground=T1,
                    padding=10)
        s.map("Glass.TCombobox",
              fieldbackground=[("readonly", GLASS), ("disabled", GLASS_2)],
              foreground=[("disabled", T4)])

        self._btn(s, "Primary.TButton",  ACCENT,       "#fff", ACCENT_DARK,    "#6db4ff",    "#c8e0ff")
        self._btn(s, "Success.TButton",  SUCCESS,      "#fff", "#22a346",      "#5ad87c",    SUCCESS_LIGHT)
        self._btn(s, "Warn.TButton",     WARNING,      "#fff", "#cc7e00",      "#fbb03b",    WARNING_LIGHT)
        self._btn(s, "Danger.TButton",   DANGER,       "#fff", "#cc2e24",      "#ff7b74",    DANGER_LIGHT)
        self._btn(s, "Glass.TButton",    GLASS,        T1,     GLASS_3,        BORDER,       T5,
                  border=BORDER,   pad=(14, 9))
        self._btn(s, "Subtle.TButton",   GLASS_2,      T3,     GLASS_3,        GLASS_3,      T4,
                  border=GLASS_3,  pad=(12, 7), font=self.fonts["caption"])
        self._btn(s, "Seg.TButton",      GLASS_3,      T3,     GLASS_2,        GLASS_3,      T4,
                  border=GLASS_3,  pad=(14, 8), font=self.fonts["caption_b"])
        self._btn(s, "SegOn.TButton",    ACCENT_LIGHT, ACCENT_TEXT, "#cce2ff", ACCENT_LIGHT, T4,
                  border=ACCENT_LIGHT, pad=(14, 8), font=self.fonts["caption_b"])

    def _btn(self, s, name, bg, fg, active, dis_bg, dis_fg,
             border=None, pad=(16, 10), font=None):
        bc = border or bg
        s.configure(name, background=bg, foreground=fg,
                    borderwidth=1, relief="flat", focuscolor=bg,
                    bordercolor=bc, lightcolor=bg, darkcolor=bg,
                    padding=pad, font=font or self.fonts["caption_b"])
        s.map(name,
              background=[("active", active), ("pressed", active), ("disabled", dis_bg)],
              foreground=[("disabled", dis_fg)])

    # ── Background canvas ──────────────────────────────────────────────────────
    def _draw_bg(self, event=None):
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        if w < 10 or h < 10:
            return
        c = self._bg_canvas
        c.delete("all")
        c.create_rectangle(0, 0, w, h, fill=BG, outline="")
        for x0, y0, x1, y1, color in [
            (-0.18*w, -0.22*h,  0.45*w,  0.38*h, BG_BLUR_1),
            ( 0.52*w, -0.12*h,  1.10*w,  0.30*h, BG_BLUR_2),
            ( 0.60*w,  0.55*h,  1.14*w,  1.10*h, BG_BLUR_3),
            (-0.10*w,  0.60*h,  0.28*w,  1.05*h, BG_BLUR_4),
        ]:
            c.create_oval(int(x0), int(y0), int(x1), int(y1), fill=color, outline="")

    # ── Card / pill helpers ────────────────────────────────────────────────────
    def _card(self, parent, bg=GLASS, border=BORDER, pad=0):
        outer = tk.Frame(parent, bg=border, highlightthickness=0, bd=0)
        inner = tk.Frame(outer, bg=bg, highlightthickness=0, bd=0)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        if pad:
            inner.configure(padx=pad, pady=pad)
        return outer, inner

    def _pill(self, parent, text, bg=GLASS_3, fg=T3, font_key="caption"):
        return tk.Label(parent, text=text, bg=bg, fg=fg,
                        font=self.fonts[font_key],
                        padx=10, pady=4, bd=0, highlightthickness=0)

    def _divider(self, parent, bg=GLASS):
        return tk.Frame(parent, bg=BORDER, height=1, highlightthickness=0, bd=0)

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self._bg_canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self._bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.root.after(50, self._draw_bg)

        outer = tk.Frame(self.root, bg=BG)
        outer.place(relx=0, rely=0, relwidth=1, relheight=1)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._build_header(outer)

        body = tk.Frame(outer, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=18)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(body)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        self._build_apps_tab()
        self._build_commands_tab()

        self._build_output_panel(outer)
        self._build_statusbar(outer)

    def _bind_shortcuts(self):
        self.root.bind_all("<Control-f>", lambda e: self._focus_search())
        self.root.bind_all("<Command-f>",  lambda e: self._focus_search())
        self.root.bind_all("<Control-r>", lambda e: self._handle_refresh_shortcut())
        self.root.bind_all("<Command-r>",  lambda e: self._handle_refresh_shortcut())
        self.root.bind_all("<Escape>",    lambda e: self._handle_escape_shortcut())

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self, parent):
        h_shell, h = self._card(parent, bg=GLASS, border=BORDER)
        h_shell.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        h.grid_columnconfigure(0, weight=1)

        left = tk.Frame(h, bg=GLASS)
        left.grid(row=0, column=0, sticky="nsew", padx=(24, 12), pady=20)

        icon_row = tk.Frame(left, bg=GLASS)
        icon_row.pack(anchor="w")
        tk.Frame(icon_row, bg=ACCENT, width=4, height=26).pack(side="left", padx=(0, 12))
        tk.Label(icon_row, text="ADB Device Manager",
                 bg=GLASS, fg=T1, font=self.fonts["hero"]).pack(side="left")

        tk.Label(left, text="USB app manager for Android \u2014 no terminal needed",
                 bg=GLASS, fg=T3, font=self.fonts["subhead"]).pack(anchor="w", pady=(6, 12))

        chip_row = tk.Frame(left, bg=GLASS)
        chip_row.pack(anchor="w")
        for txt, bg, fg in [
            ("No root required",   ACCENT_LIGHT, ACCENT_TEXT),
            ("USB Debugging",      GLASS_3,      T3),
            ("Multi-device aware", GLASS_3,      T3),
        ]:
            self._pill(chip_row, txt, bg, fg).pack(side="left", padx=(0, 8))

        tk.Frame(h, bg=BORDER, width=1).grid(row=0, column=1, sticky="ns", pady=16)

        right = tk.Frame(h, bg=GLASS)
        right.grid(row=0, column=2, sticky="nsew", padx=(16, 24), pady=20)
        right.grid_columnconfigure(0, weight=1)

        top_row = tk.Frame(right, bg=GLASS)
        top_row.grid(row=0, column=0, sticky="ew")
        top_row.grid_columnconfigure(0, weight=1)
        tk.Label(top_row, text="TARGET DEVICE", bg=GLASS, fg=T4,
                 font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        self.header_status_badge = self._pill(top_row, "No device", GLASS_3, T3)
        self.header_status_badge.grid(row=0, column=1, sticky="e")

        picker = tk.Frame(right, bg=GLASS)
        picker.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        picker.grid_columnconfigure(0, weight=1)
        self.device_combo = ttk.Combobox(
            picker, textvariable=self.selected_serial,
            state="readonly", style="Glass.TCombobox", width=44)
        self.device_combo.grid(row=0, column=0, sticky="ew")
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_selected)

        self.refresh_devices_btn = ttk.Button(
            picker, text="\u27f3  Refresh", style="Glass.TButton",
            command=self._refresh_devices)
        self.refresh_devices_btn.grid(row=0, column=1, padx=(10, 0))

        self.header_device_note_label = tk.Label(
            right,
            text="Connect your phone over USB and approve the debugging prompt.",
            bg=GLASS, fg=T4, font=self.fonts["caption"],
            justify="left", wraplength=400)
        self.header_device_note_label.grid(row=2, column=0, sticky="w")

    # ── Apps tab ───────────────────────────────────────────────────────────────
    def _build_apps_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=0)
        tab.grid_rowconfigure(0, weight=1)
        self.notebook.add(tab, text="  \U0001f4f1  Apps  ")

        # Left: browser
        left = tk.Frame(tab, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(10, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        tb_shell, tb = self._card(left, bg=GLASS, border=BORDER)
        tb_shell.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._build_browser_toolbar(tb)

        tbl_shell, tbl = self._card(left, bg=GLASS, border=BORDER)
        tbl_shell.grid(row=1, column=0, sticky="nsew")
        tbl.grid_rowconfigure(0, weight=1)
        tbl.grid_columnconfigure(0, weight=1)
        self._build_package_table(tbl)

        # Right: sidebar
        sidebar = tk.Frame(tab, bg=BG, width=298)
        sidebar.grid(row=0, column=1, sticky="nsew", pady=(10, 10))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        dev_shell, dev_card = self._card(sidebar, bg=GLASS, border=BORDER)
        dev_shell.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._build_device_card(dev_card)

        sel_shell, sel_card = self._card(sidebar, bg=GLASS_2, border=BORDER)
        sel_shell.grid(row=1, column=0, sticky="nsew")
        self._build_selection_card(sel_card)

    def _build_browser_toolbar(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        row0 = tk.Frame(parent, bg=GLASS)
        row0.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        row0.grid_columnconfigure(0, weight=1)

        lbl_row = tk.Frame(row0, bg=GLASS)
        lbl_row.grid(row=0, column=0, sticky="w")
        tk.Label(lbl_row, text="Package Library", bg=GLASS, fg=T1,
                 font=self.fonts["heading"]).pack(side="left")
        self.pkg_count_label = tk.Label(lbl_row, text="", bg=GLASS, fg=T4,
                                         font=self.fonts["caption"])
        self.pkg_count_label.pack(side="left", padx=(10, 0), pady=(2, 0))

        rhs = tk.Frame(row0, bg=GLASS)
        rhs.grid(row=0, column=1, sticky="e")

        self.search_entry = ttk.Entry(rhs, textvariable=self.search_var,
                                       style="Glass.TEntry", width=30,
                                       font=self.fonts["body"])
        self.search_entry.grid(row=0, column=0, ipady=2)
        self.search_entry.insert(0, "Search packages\u2026")
        self.search_entry.configure(foreground=T4)
        self.search_entry.bind("<FocusIn>",  self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)

        self.clear_search_btn = ttk.Button(rhs, text="\u2715", style="Subtle.TButton",
                                            command=self._clear_search, width=3)
        self.clear_search_btn.grid(row=0, column=1, padx=(6, 0))

        self.refresh_apps_btn = ttk.Button(rhs, text="\u27f3  Refresh Apps",
                                            style="Glass.TButton", command=self._refresh_apps)
        self.refresh_apps_btn.grid(row=0, column=2, padx=(6, 0))

        self.export_txt_btn = ttk.Button(rhs, text="\u2191 TXT",
                                          style="Subtle.TButton", command=self._export_txt)
        self.export_txt_btn.grid(row=0, column=3, padx=(6, 0))

        self.export_csv_btn = ttk.Button(rhs, text="\u2191 CSV",
                                          style="Subtle.TButton", command=self._export_csv)
        self.export_csv_btn.grid(row=0, column=4, padx=(4, 0))

        self._divider(parent).grid(row=1, column=0, sticky="ew")

        row1 = tk.Frame(parent, bg=GLASS)
        row1.grid(row=2, column=0, sticky="ew", padx=18, pady=(10, 14))
        row1.grid_columnconfigure(1, weight=1)

        seg = tk.Frame(row1, bg=GLASS)
        seg.grid(row=0, column=0, sticky="w")
        self.filter_buttons = {}
        for i, (key, label) in enumerate(FILTER_META):
            btn = ttk.Button(seg, text=label, style="Seg.TButton",
                             command=lambda k=key: self._set_filter(k))
            btn.grid(row=0, column=i, padx=(0, 4))
            self.filter_buttons[key] = btn
        self._update_filter_button_styles()

        self.filter_summary_label = tk.Label(row1, text="", bg=GLASS, fg=T4,
                                              font=self.fonts["caption"], anchor="e")
        self.filter_summary_label.grid(row=0, column=1, sticky="e")

    def _build_package_table(self, parent):
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        cols = ("Package Name", "Type", "Status")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings",
                                  selectmode="browse")
        for col, width, stretch, anchor in [
            ("Package Name", 520, True,  "w"),
            ("Type",         110, False, "center"),
            ("Status",       120, False, "center"),
        ]:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_tree(c))
            self.tree.column(col, width=width, minwidth=80,
                             stretch=stretch, anchor=anchor)

        self.tree.tag_configure("odd",      background=ROW_ODD)
        self.tree.tag_configure("even",     background=ROW_EVEN)
        self.tree.tag_configure("user",     foreground=SUCCESS_TEXT)
        self.tree.tag_configure("system",   foreground=WARNING_TEXT)
        self.tree.tag_configure("disabled", foreground=T4)

        vsb = ttk.Scrollbar(parent, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_package_selected)
        self.tree.bind("<Double-1>",         self._on_package_double_click)

        self.table_state_label = tk.Label(
            parent, text="", bg=GLASS, fg=T3,
            font=self.fonts["subhead"], justify="center", wraplength=360)

    # ── Sidebar: device info ───────────────────────────────────────────────────
    def _build_device_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(parent, bg=GLASS)
        hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))
        hdr.grid_columnconfigure(0, weight=1)
        tk.Label(hdr, text="DEVICE", bg=GLASS, fg=T4,
                 font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        self.device_badge_label = self._pill(hdr, "Waiting", GLASS_3, T4)
        self.device_badge_label.grid(row=0, column=1, sticky="e")

        self.device_name_label = tk.Label(
            parent, text="No device", bg=GLASS, fg=T1,
            font=self.fonts["title"], anchor="w")
        self.device_name_label.grid(row=1, column=0, sticky="ew",
                                     padx=18, pady=(10, 2))

        self.device_summary_label = tk.Label(
            parent, text="Choose a device above",
            bg=GLASS, fg=T3, font=self.fonts["caption"],
            justify="left", wraplength=256, anchor="w")
        self.device_summary_label.grid(row=2, column=0, sticky="ew",
                                        padx=18, pady=(0, 12))

        tiles = tk.Frame(parent, bg=GLASS)
        tiles.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        for i in range(3):
            tiles.grid_columnconfigure(i, weight=1)

        self.device_metric_labels = {}
        for i, (title, key) in enumerate([
            ("Brand",   "manufacturer"),
            ("Android", "android_version"),
            ("SDK",     "sdk"),
        ]):
            t_shell, tile = self._card(tiles, bg=GLASS_3, border=BORDER_2)
            t_shell.grid(row=0, column=i, sticky="nsew",
                         padx=(0 if i == 0 else 4, 0))
            tk.Label(tile, text=title, bg=GLASS_3, fg=T4,
                     font=self.fonts["label"],
                     padx=8).pack(anchor="w", pady=(6, 0))
            lbl = tk.Label(tile, text="--", bg=GLASS_3, fg=T1,
                           font=self.fonts["caption_b"], padx=8)
            lbl.pack(anchor="w", pady=(2, 8))
            self.device_metric_labels[key] = lbl

        details = tk.Frame(parent, bg=GLASS)
        details.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        details.grid_columnconfigure(1, weight=1)

        self.info_labels = {}
        for i, (label, key) in enumerate([
            ("Model",  "model"),
            ("Serial", "serial"),
            ("Build",  "fingerprint"),
        ]):
            tk.Label(details, text=label, bg=GLASS, fg=T4,
                     font=self.fonts["label"], anchor="w",
                     width=7).grid(row=i, column=0, sticky="nw", pady=(0, 6))
            v = tk.Label(details, text="--", bg=GLASS, fg=T2,
                         font=self.fonts["caption"],
                         justify="left", wraplength=196, anchor="w")
            v.grid(row=i, column=1, sticky="ew", padx=(6, 0), pady=(0, 6))
            self.info_labels[key] = v

    # ── Sidebar: selection / actions ───────────────────────────────────────────
    def _build_selection_card(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(parent, bg=GLASS_2)
        hdr.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))
        hdr.grid_columnconfigure(0, weight=1)
        tk.Label(hdr, text="SELECTED PACKAGE", bg=GLASS_2, fg=T4,
                 font=self.fonts["label"]).grid(row=0, column=0, sticky="w")
        self.selection_badge_label = self._pill(hdr, "None", GLASS_3, T4)
        self.selection_badge_label.grid(row=0, column=1, sticky="e")

        self.selected_pkg_title_label = tk.Label(
            parent, text="No package selected",
            bg=GLASS_2, fg=T1, font=self.fonts["heading"],
            anchor="w", justify="left", wraplength=258)
        self.selected_pkg_title_label.grid(row=1, column=0, sticky="ew",
                                            padx=18, pady=(12, 6))

        self.selected_pkg_note_label = tk.Label(
            parent,
            text="Select a package in the table to see its type, status, and actions.",
            bg=GLASS_2, fg=T3, font=self.fonts["caption"],
            justify="left", wraplength=258, anchor="w")
        self.selected_pkg_note_label.grid(row=2, column=0, sticky="ew",
                                           padx=18, pady=(0, 12))

        chips = tk.Frame(parent, bg=GLASS_2)
        chips.grid(row=3, column=0, sticky="w", padx=18, pady=(0, 14))
        self.pkg_type_chip   = self._pill(chips, "Type: --",   GLASS_3, T4)
        self.pkg_type_chip.pack(side="left", padx=(0, 6))
        self.pkg_status_chip = self._pill(chips, "Status: --", GLASS_3, T4)
        self.pkg_status_chip.pack(side="left")

        self._divider(parent, GLASS_2).grid(row=4, column=0, sticky="ew")

        actions = tk.Frame(parent, bg=GLASS_2)
        actions.grid(row=5, column=0, sticky="ew", padx=18, pady=(14, 0))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=1)

        self.action_buttons = {}
        specs = [
            ("enable",    "\u2713  Enable",       "Success.TButton", self._action_enable,    0, 0, {}),
            ("disable",   "\u2298  Disable",      "Warn.TButton",    self._action_disable,   0, 1, {}),
            ("appinfo",   "\u24d8  App Info",     "Glass.TButton",   self._action_open_info, 1, 0, {}),
            ("copy",      "\u2398  Copy Name",    "Glass.TButton",   self._action_copy,      1, 1, {}),
            ("uninstall", "\u232b  Uninstall for User",
             "Danger.TButton", self._action_uninstall, 2, 0, {"columnspan": 2}),
        ]
        for key, text, style, cmd, row, col, extra in specs:
            btn = ttk.Button(actions, text=text, style=style,
                             command=cmd, state="disabled")
            btn.grid(row=row, column=col, sticky="ew",
                     padx=(0, 4 if col == 0 and "columnspan" not in extra else 0),
                     pady=(0, 8), **extra)
            self.action_buttons[key] = btn

        self.selection_footer_label = tk.Label(
            parent,
            text="System apps show extra confirmation before destructive actions.",
            bg=GLASS_2, fg=T5, font=self.fonts["caption"],
            justify="left", wraplength=258, anchor="w")
        self.selection_footer_label.grid(row=6, column=0, sticky="ew",
                                          padx=18, pady=(0, 18))

    # ── Commands tab ───────────────────────────────────────────────────────────
    def _build_commands_tab(self):
        tab = tk.Frame(self.notebook, bg=BG)
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)
        self.notebook.add(tab, text="  \u2328  Commands  ")

        comp_shell, comp = self._card(tab, bg=GLASS, border=BORDER)
        comp_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=10)
        comp.grid_columnconfigure(0, weight=1)

        tk.Label(comp, text="Shell Command", bg=GLASS, fg=T1,
                 font=self.fonts["heading"]).grid(
            row=0, column=0, sticky="w", padx=22, pady=(22, 0))
        tk.Label(comp,
                 text="Runs on the currently selected device. Good for advanced read-only checks.",
                 bg=GLASS, fg=T3, font=self.fonts["caption"],
                 justify="left", wraplength=560).grid(
            row=1, column=0, sticky="w", padx=22, pady=(6, 16))

        device_row = tk.Frame(comp, bg=GLASS)
        device_row.grid(row=2, column=0, sticky="ew", padx=22)
        self.command_device_label = self._pill(device_row, "No device", GLASS_3, T3)
        self.command_device_label.pack(side="left")
        self.command_prefix_label = tk.Label(
            device_row,
            text="  \u2192  adb -s <device> shell <command>",
            bg=GLASS, fg=T4, font=self.fonts["caption"])
        self.command_prefix_label.pack(side="left", padx=(6, 0))

        cmd_row = tk.Frame(comp, bg=GLASS)
        cmd_row.grid(row=3, column=0, sticky="ew", padx=22, pady=(14, 0))
        cmd_row.grid_columnconfigure(0, weight=1)

        self.custom_cmd_entry = ttk.Entry(
            cmd_row, textvariable=self.custom_cmd_var,
            style="Glass.TEntry", font=self.fonts["mono"])
        self.custom_cmd_entry.grid(row=0, column=0, sticky="ew", ipady=4)
        self.custom_cmd_entry.bind("<Return>", lambda e: self._run_custom_command())

        self.run_command_btn = ttk.Button(
            cmd_row, text="\u25b6  Run", style="Primary.TButton",
            command=self._run_custom_command)
        self.run_command_btn.grid(row=0, column=1, padx=(10, 0))

        samples_f = tk.Frame(comp, bg=GLASS)
        samples_f.grid(row=4, column=0, sticky="w", padx=22, pady=(18, 22))
        tk.Label(samples_f, text="QUICK EXAMPLES", bg=GLASS, fg=T4,
                 font=self.fonts["label"]).pack(anchor="w", pady=(0, 8))
        sr = tk.Frame(samples_f, bg=GLASS)
        sr.pack(anchor="w")
        for cmd in ["pm list packages", "pm path com.android.chrome",
                    "settings get secure android_id"]:
            ttk.Button(sr, text=cmd, style="Subtle.TButton",
                       command=lambda v=cmd: self._set_sample_command(v)
                       ).pack(side="left", padx=(0, 8))

        note_shell, note = self._card(tab, bg=GLASS_2, border=BORDER)
        note_shell.grid(row=0, column=1, sticky="nsew", pady=10)
        note.grid_columnconfigure(0, weight=1)

        tk.Label(note, text="Notes", bg=GLASS_2, fg=T1,
                 font=self.fonts["heading"]).grid(
            row=0, column=0, sticky="w", padx=20, pady=(20, 12))

        for i, txt in enumerate([
            "Empty commands are blocked automatically.",
            "Output, stderr, exit code, and timestamps appear in the panel below.",
            "If you modify package state here, use Refresh Apps to sync the table.",
            "Commands run through adb shell on the selected device only.",
            "\u2318R / Ctrl+R  \u2014  Refresh\n\u2318F / Ctrl+F  \u2014  Focus search\nEsc  \u2014  Clear search",
        ]):
            tk.Label(note, text=txt, bg=GLASS_2, fg=T3,
                     font=self.fonts["caption"],
                     justify="left", wraplength=320, anchor="w").grid(
                row=i+1, column=0, sticky="w", padx=20, pady=(0, 10))

    # ── Output panel ───────────────────────────────────────────────────────────
    def _build_output_panel(self, parent):
        shell, panel = self._card(parent, bg=TERM_PANEL, border=TERM_BORDER)
        shell.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 8))

        hdr = tk.Frame(panel, bg=TERM_PANEL)
        hdr.pack(fill="x", padx=18, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)

        lh = tk.Frame(hdr, bg=TERM_PANEL)
        lh.grid(row=0, column=0, sticky="w")
        tk.Label(lh, text="Command Output", bg=TERM_PANEL, fg=TERM_TEXT,
                 font=self.fonts["heading"]).pack(side="left")
        self.output_meta_label = tk.Label(
            lh, text="  \u00b7  No commands run yet",
            bg=TERM_PANEL, fg=TERM_MUTED, font=self.fonts["caption"])
        self.output_meta_label.pack(side="left", pady=(2, 0))

        self.output_badge_label = self._pill(hdr, "Idle", TERM_PANEL, TERM_MUTED)
        self.output_badge_label.grid(row=0, column=1, sticky="e")

        btn_row = tk.Frame(panel, bg=TERM_PANEL)
        btn_row.pack(fill="x", padx=18, pady=(0, 8))
        ttk.Button(btn_row, text="Copy", style="Subtle.TButton",
                   command=self._copy_output).pack(side="right")
        ttk.Button(btn_row, text="Clear", style="Subtle.TButton",
                   command=self._clear_output).pack(side="right", padx=(0, 6))

        text_f = tk.Frame(panel, bg=TERM_BG)
        text_f.pack(fill="both", expand=True, padx=18, pady=(0, 14))

        self.output_text = tk.Text(
            text_f, height=8, bg=TERM_BG, fg=TERM_TEXT,
            font=self.fonts["mono_sm"], wrap="word",
            bd=0, highlightthickness=0,
            insertbackground=TERM_TEXT, state="disabled")

        mf = self.fonts["mono_sm"]
        bold_mono = (mf[0], mf[1], "bold")
        self.output_text.tag_configure("header",  foreground="#79b8ff", font=bold_mono)
        self.output_text.tag_configure("success", foreground="#85e89d")
        self.output_text.tag_configure("error",   foreground="#f97583")
        self.output_text.tag_configure("warning", foreground="#ffab70")
        self.output_text.tag_configure("muted",   foreground=TERM_MUTED)

        vsb = ttk.Scrollbar(text_f, orient="vertical",
                             command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=vsb.set)
        self.output_text.pack(side="left", fill="both", expand=True,
                               padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", padx=(0, 8), pady=8)

    # ── Status bar ─────────────────────────────────────────────────────────────
    def _build_statusbar(self, parent):
        bar = tk.Frame(parent, bg=BG)
        bar.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        bar.grid_columnconfigure(0, weight=1)

        self.status_label = tk.Label(bar, text="Ready", bg=BG, fg=T4,
                                      font=self.fonts["caption"], anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w")

        self.status_context_label = tk.Label(bar, text="", bg=BG, fg=T5,
                                              font=self.fonts["caption"], anchor="e")
        self.status_context_label.grid(row=0, column=1, sticky="e", padx=(18, 12))

        self.progress = ttk.Progressbar(bar, mode="indeterminate",
                                         style="TProgressbar", length=130)
        self.progress.grid(row=0, column=2, sticky="e")
        self._set_progress(False)

    # ── Search placeholder ─────────────────────────────────────────────────────
    def _search_focus_in(self, event):
        if self._search_placeholder:
            self.search_entry.delete(0, "end")
            self.search_entry.configure(foreground=T1)
            self._search_placeholder = False

    def _search_focus_out(self, event):
        if not self.search_var.get():
            self.search_entry.insert(0, "Search packages\u2026")
            self.search_entry.configure(foreground=T4)
            self._search_placeholder = True

    # ══════════════════════════════════════════════════════════════════════════
    # Logic (unchanged from previous version)
    # ══════════════════════════════════════════════════════════════════════════

    def _set_status(self, message, color=None):
        self.status_label.configure(text=message, fg=color or T4)
        self._refresh_status_context()

    def _set_progress(self, active):
        if active:
            self.progress.start(11)
        else:
            self.progress.stop()

    def _begin_job(self, message=None):
        self._active_jobs += 1
        self._set_progress(True)
        if message:
            self._set_status(message)
        self._refresh_interactive_states()

    def _end_job(self):
        self._active_jobs = max(0, self._active_jobs - 1)
        self._set_progress(self._active_jobs > 0)
        self._refresh_interactive_states()

    def _set_output_badge(self, text, bg, fg, meta):
        self.output_badge_label.configure(text=text, bg=bg, fg=fg)
        self.output_meta_label.configure(text=f"  \u00b7  {meta}")

    def _refresh_status_context(self):
        serial  = self._get_serial() or "No device"
        visible = len(self.visible_packages)
        total   = len(self.all_packages)
        flabel  = dict(FILTER_META).get(self.current_filter, self.current_filter.title())
        self.status_context_label.configure(
            text=f"{serial}   \u00b7   {visible}/{total} packages   \u00b7   {flabel}")

        if hasattr(self, "command_prefix_label"):
            if self._is_device_ready():
                self.command_prefix_label.configure(
                    text=f"  \u2192  adb -s {serial} shell <command>")
                self.command_device_label.configure(
                    text=serial, bg=ACCENT_LIGHT, fg=ACCENT_TEXT)
            else:
                self.command_prefix_label.configure(
                    text="  \u2192  adb -s <device> shell <command>")
                self.command_device_label.configure(
                    text="No device", bg=GLASS_3, fg=T3)

    def _friendly_device_status(self, status):
        return {"device": "Ready", "unauthorized": "Unauthorized",
                "offline": "Offline"}.get(status, status.title() if status else "Unknown")

    def _set_device_badges(self, text, bg, fg):
        self.header_status_badge.configure(text=text, bg=bg, fg=fg)
        self.device_badge_label.configure(text=text, bg=bg, fg=fg)

    def _get_serial(self):
        value = self.selected_serial.get().strip()
        if not value:
            return None
        return self.device_label_map.get(value, value)

    def _device_record(self, serial=None):
        serial = serial or self._get_serial()
        if not serial:
            return None
        return next((d for d in self.devices if d["serial"] == serial), None)

    def _is_device_ready(self):
        r = self._device_record()
        return bool(r and r.get("status") == "device")

    def _lookup_package(self, package_name):
        if not package_name:
            return None
        return next((p for p in self.all_packages if p["package"] == package_name), None)

    def _handle_thread_error(self, result, user_message):
        if isinstance(result, Exception):
            ts = datetime.now().strftime("%H:%M:%S")
            self._append_output(f"\n[{ts}] Unexpected error\n", "error")
            self._append_output(f"{result}\n", "error")
            self._set_status(user_message, DANGER)
            self._set_output_badge("Error", DANGER, "#fff", user_message)
            return True
        return False

    def run_in_thread(self, task_function, callback_function=None):
        def worker():
            try:
                result = task_function()
            except Exception as exc:
                result = exc
            if callback_function:
                self.root.after(0, lambda value=result: callback_function(value))
        threading.Thread(target=worker, daemon=True).start()

    def _append_output(self, text, tag=""):
        self.output_text.configure(state="normal")
        self.output_text.insert("end", text, tag)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")

    def _clear_output(self):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self._set_output_badge("Idle", TERM_PANEL, TERM_MUTED, "No commands run yet.")

    def _copy_output(self):
        content = self.output_text.get("1.0", "end").strip()
        if not content:
            self._set_status("No output to copy.", WARNING)
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self._set_status("Copied command output to clipboard.", SUCCESS)

    def _log_command(self, command_text, stdout, stderr, code, timestamp):
        sep = "\u2500" * 60
        result_text = "\u2713 Success" if code == 0 else "\u2717 Failed"
        result_tag  = "success" if code == 0 else "error"
        self._append_output(f"\n{sep}\n", "muted")
        self._append_output(f"[{timestamp}] {result_text}\n", result_tag)
        self._append_output(f"$ {command_text}\n", "header")
        if stdout:
            self._append_output("stdout:\n", "muted")
            self._append_output(stdout + "\n", "success" if code == 0 else "")
        if stderr:
            self._append_output("stderr:\n", "muted")
            self._append_output(stderr + "\n", "error")
        if not stdout and not stderr:
            self._append_output("(no output)\n", "muted")
        self._append_output(f"exit {code}\n", result_tag)
        if code == 0:
            self._set_output_badge(
                "Success", SUCCESS, "#fff", f"Last command succeeded at {timestamp}.")
        else:
            self._set_output_badge(
                "Failed", DANGER, "#fff", f"Last command failed at {timestamp}.")

    def _refresh_interactive_states(self):
        busy         = self._active_jobs > 0
        device_ready = self._is_device_ready()
        has_visible  = bool(self.visible_packages)
        has_sel      = bool(self.selected_package_name and
                            self._lookup_package(self.selected_package_name))
        has_search   = (bool(self.search_var.get().strip()) and
                        not self._search_placeholder)
        has_devices  = bool(self.devices)
        has_packages = bool(self.all_packages)
        has_cmd      = bool(self.custom_cmd_var.get().strip())

        self.device_combo.configure(
            state="readonly" if has_devices and not self._devices_loading else "disabled")
        self.refresh_devices_btn.configure(
            state="disabled" if self._devices_loading else "normal")
        self.refresh_apps_btn.configure(
            state="normal" if device_ready and not busy else "disabled")
        self.export_txt_btn.configure(
            state="normal" if has_visible and not busy else "disabled")
        self.export_csv_btn.configure(
            state="normal" if has_visible and not busy else "disabled")
        self.clear_search_btn.configure(
            state="normal" if has_search and not busy else "disabled")
        self.search_entry.configure(state="normal" if not busy else "disabled")
        self.custom_cmd_entry.configure(state="normal" if not busy else "disabled")
        self.run_command_btn.configure(
            state="normal" if device_ready and has_cmd and not busy else "disabled")
        for btn in self.filter_buttons.values():
            btn.configure(state="normal" if has_packages and not busy else "disabled")
        for btn in self.action_buttons.values():
            btn.configure(
                state="normal" if device_ready and has_sel and not busy else "disabled")

    # ── ADB startup ────────────────────────────────────────────────────────────
    def _check_adb_and_load(self):
        self._begin_job("Checking ADB availability\u2026")

        def task():
            adb_path = adb_manager.get_adb_path()
            if not adb_path:
                return None, None
            stdout, _, code, _ = adb_manager.run_adb_command(["version"])
            if code != 0:
                return adb_path, None
            return adb_path, stdout.splitlines()[0] if stdout else "Unknown version"

        def callback(result):
            self._end_job()
            if self._handle_thread_error(result, "Unable to verify ADB availability."):
                return
            adb_path, version_line = result
            if not adb_path:
                messagebox.showerror(
                    "ADB Not Found",
                    "ADB not found.\n\nInstall Android Platform Tools or place the "
                    "adb executable inside this project folder.")
                self._set_status("ADB not found.", DANGER)
                self._set_device_badges("ADB missing", DANGER_LIGHT, DANGER)
                self._clear_device_info("ADB not found.")
                self._reset_package_browser("ADB not found.\nInstall Android Platform Tools.")
                return
            version_text = version_line or "ADB detected"
            self._append_output(f"ADB detected: {version_text}\n", "success")
            self._set_status(f"ADB ready: {version_text}", SUCCESS)
            self.header_device_note_label.configure(
                text="ADB is ready. Scanning for devices\u2026")
            self._refresh_devices()

        self.run_in_thread(task, callback)

    def _refresh_devices(self):
        if self._devices_loading:
            return
        self._devices_loading = True
        self._begin_job("Scanning for connected devices\u2026")

        def task():
            return adb_manager.list_devices()

        def callback(result):
            self._devices_loading = False
            self._end_job()
            if self._handle_thread_error(result, "Unable to scan devices."):
                return

            devices, error_message = result
            previous_serial = self._get_serial()
            self.devices = devices
            self.device_label_map = {}
            combo_values = []
            for device in devices:
                label = (f"{device['serial']}  \u00b7  "
                         f"{self._friendly_device_status(device['status'])}")
                combo_values.append(label)
                self.device_label_map[label] = device["serial"]
            self.device_combo["values"] = combo_values

            if error_message:
                self._append_output(f"Device scan note: {error_message}\n", "warning")

            if not devices:
                self.selected_serial.set("")
                self._loaded_serial = None
                self._set_device_badges("No device", WARNING_LIGHT, WARNING)
                self.header_device_note_label.configure(
                    text="No Android device connected. Connect a phone and enable USB debugging.")
                self._set_status(
                    "No Android device connected. Enable USB debugging.", WARNING)
                self._clear_device_info("No device detected yet.")
                self._reset_package_browser(
                    "No Android device connected.\nConnect a phone and enable USB debugging.")
                self._refresh_status_context()
                self._refresh_interactive_states()
                return

            matching_label = next(
                (label for label, serial in self.device_label_map.items()
                 if serial == previous_serial), None)

            if matching_label:
                self.selected_serial.set(matching_label)
                self._on_device_selected(None)
            elif len(devices) == 1:
                self.selected_serial.set(combo_values[0])
                self._on_device_selected(None)
            else:
                self.selected_serial.set("")
                self._loaded_serial = None
                self._set_device_badges("Choose device", WARNING_LIGHT, WARNING)
                self.header_device_note_label.configure(
                    text=f"{len(devices)} devices detected. Choose the one you want to manage.")
                self._set_status("Multiple devices detected. Select one.", WARNING)
                self._clear_device_info("Multiple devices connected. Choose one above.")
                self._reset_package_browser("Multiple devices connected.\nSelect the device to manage.")

            self._refresh_status_context()
            self._refresh_interactive_states()

        self.run_in_thread(task, callback)

    def _on_device_selected(self, event):
        serial = self._get_serial()
        if not serial:
            self._set_device_badges("No device", GLASS_3, T4)
            self._clear_device_info("Choose a connected device.")
            self._reset_package_browser("Select a device to load packages.")
            self._refresh_status_context()
            self._refresh_interactive_states()
            return

        record = self._device_record(serial)
        status = record["status"] if record else "unknown"

        if status == "unauthorized":
            self._loaded_serial = None
            self._set_device_badges("Unauthorized", WARNING_LIGHT, WARNING)
            self.header_device_note_label.configure(
                text="Approve USB debugging on your phone, then refresh devices.")
            self._clear_device_info("Phone connected but not authorized.")
            self._reset_package_browser("Device unauthorized.\nApprove USB debugging on the phone.")
            self._set_status("Device unauthorized.", WARNING)
            messagebox.showwarning(
                "Unauthorized Device",
                "Device unauthorized.\n\nAllow USB debugging on your phone, then refresh devices.")
            self._refresh_status_context()
            self._refresh_interactive_states()
            return

        if status == "offline":
            self._loaded_serial = None
            self._set_device_badges("Offline", DANGER_LIGHT, DANGER)
            self.header_device_note_label.configure(
                text="Device offline. Reconnect and refresh.")
            self._clear_device_info("Device is offline.")
            self._reset_package_browser("Device offline.\nReconnect and try again.")
            self._set_status("Device is offline.", DANGER)
            self._refresh_status_context()
            self._refresh_interactive_states()
            return

        if status != "device":
            self._loaded_serial = None
            friendly = self._friendly_device_status(status)
            self._set_device_badges(friendly, WARNING_LIGHT, WARNING)
            self._clear_device_info(f"Device status: {friendly}.")
            self._reset_package_browser(f"Device status: {friendly}.")
            self._set_status(f"Device status: {friendly}.", WARNING)
            self._refresh_status_context()
            self._refresh_interactive_states()
            return

        self._set_device_badges("Ready", SUCCESS_LIGHT, SUCCESS_TEXT)
        self.header_device_note_label.configure(
            text=f"Managing {serial}. Loading\u2026")

        if serial == self._loaded_serial and self.all_packages:
            self._set_status(f"Ready on {serial}.", SUCCESS)
            self._refresh_status_context()
            self._refresh_interactive_states()
            return

        self._loaded_serial = serial
        self._set_status(f"Loading data for {serial}\u2026")
        self._clear_device_info(f"Loading device info for {serial}\u2026")
        self._reset_package_browser("Loading installed packages\u2026")
        self._load_device_info(serial)
        self._refresh_apps()

    def _clear_device_info(self, message):
        self.device_name_label.configure(text="No device")
        self.device_summary_label.configure(text=message)
        for lbl in self.device_metric_labels.values():
            lbl.configure(text="--")
        for lbl in self.info_labels.values():
            lbl.configure(text="--")

    def _load_device_info(self, serial):
        self._begin_job("Loading device information\u2026")

        def task():
            return adb_manager.get_device_info(serial)

        def callback(result):
            self._end_job()
            if self._handle_thread_error(result, "Unable to load device information."):
                return
            info = result
            manufacturer    = info.get("manufacturer",    "N/A")
            model           = info.get("model",           "N/A")
            android_version = info.get("android_version", "N/A")
            sdk             = info.get("sdk",             "N/A")
            fingerprint     = info.get("fingerprint",     "N/A")

            display_name = model if model and model != "N/A" else serial
            bits = []
            if manufacturer and manufacturer != "N/A":
                bits.append(manufacturer)
            if android_version and android_version != "N/A":
                bits.append(f"Android {android_version}")
            bits.append(f"Serial {serial}")

            self.device_name_label.configure(text=display_name)
            self.device_summary_label.configure(text=" \u00b7 ".join(bits))
            self.device_metric_labels["manufacturer"].configure(text=manufacturer or "N/A")
            self.device_metric_labels["android_version"].configure(text=android_version or "N/A")
            self.device_metric_labels["sdk"].configure(text=sdk or "N/A")
            self.info_labels["model"].configure(text=model or "N/A")
            self.info_labels["serial"].configure(text=serial)
            self.info_labels["fingerprint"].configure(text=fingerprint or "N/A")
            self.header_device_note_label.configure(
                text=f"{display_name} is ready.")

        self.run_in_thread(task, callback)

    # ── Packages ───────────────────────────────────────────────────────────────
    def _reset_package_browser(self, message):
        self.all_packages         = []
        self.visible_packages     = []
        self.selected_package_name= None
        self._clear_tree()
        self._show_table_state(message)
        self.pkg_count_label.configure(text="")
        self.filter_summary_label.configure(text="Load a ready device to browse packages.")
        self._update_filter_counts()
        self._update_selected_package_card(None)
        self._refresh_status_context()
        self._refresh_interactive_states()

    def _refresh_apps(self):
        serial = self._get_serial()
        if not serial or not self._is_device_ready():
            self._set_status("Select a ready device before loading apps.", WARNING)
            return
        if self._apps_loading:
            self._set_status("Package list is already loading\u2026", WARNING)
            return

        self._apps_loading = True
        self._begin_job("Loading installed packages\u2026")
        self._show_table_state("Loading installed packages\u2026")
        self.pkg_count_label.configure(text="Loading\u2026")

        def task():
            return app_manager.classify_packages(serial)

        def callback(result):
            self._apps_loading = False
            self._end_job()
            if self._handle_thread_error(result, "Unable to load installed packages."):
                return
            packages, error_message = result
            self.all_packages = packages
            if error_message:
                self._append_output(f"Package load note: {error_message}\n", "warning")
            self._update_filter_counts()
            self._apply_filter_and_search()
            self._set_status(f"Loaded {len(packages)} packages for {serial}.", SUCCESS)
            self.header_device_note_label.configure(
                text=f"{len(packages)} packages loaded for {serial}.")

        self.run_in_thread(task, callback)

    def _filter_matches(self, package):
        if self.current_filter == "all":      return True
        if self.current_filter == "user":     return package["type"]   == "User"
        if self.current_filter == "system":   return package["type"]   == "System"
        if self.current_filter == "enabled":  return package["status"] == "Enabled"
        if self.current_filter == "disabled": return package["status"] == "Disabled"
        return True

    def _apply_filter_and_search(self):
        raw_search = self.search_var.get().strip()
        search     = "" if self._search_placeholder else raw_search.lower()

        filtered = [
            p for p in self.all_packages
            if self._filter_matches(p) and
            (not search or search in p["package"].lower())
        ]

        if self._sort_col:
            key_name = {"Package Name": "package",
                        "Type": "type", "Status": "status"}[self._sort_col]
            filtered.sort(key=lambda item: item[key_name].lower(),
                          reverse=self._sort_reverse)

        self.visible_packages = filtered
        self._populate_tree(filtered)

        total   = len(self.all_packages)
        visible = len(filtered)
        flabel  = dict(FILTER_META).get(self.current_filter, self.current_filter.title())

        if total == 0:
            self.pkg_count_label.configure(text="")
            self.filter_summary_label.configure(text="Load a ready device to browse packages.")
            self._show_table_state("No packages loaded yet.")
        elif visible == 0:
            self.pkg_count_label.configure(text=f"0 of {total}")
            self.filter_summary_label.configure(
                text=f"No packages match \u2018{flabel}\u2019 and your search.")
            self._show_table_state("No packages match the current filter or search.")
        else:
            self.pkg_count_label.configure(text=f"{visible} of {total}")
            if search:
                self.filter_summary_label.configure(
                    text=f"{visible} package(s) in \u2018{flabel}\u2019 matching \u2018{raw_search}\u2019")
            else:
                self.filter_summary_label.configure(
                    text=f"{visible} package(s) \u00b7 \u2018{flabel}\u2019 filter")
            self._hide_table_state()

        self._refresh_status_context()
        self._refresh_interactive_states()

    def _update_filter_counts(self):
        counts = {
            "all":      len(self.all_packages),
            "user":     sum(1 for p in self.all_packages if p["type"]   == "User"),
            "system":   sum(1 for p in self.all_packages if p["type"]   == "System"),
            "enabled":  sum(1 for p in self.all_packages if p["status"] == "Enabled"),
            "disabled": sum(1 for p in self.all_packages if p["status"] == "Disabled"),
        }
        for key, label in FILTER_META:
            self.filter_buttons[key].configure(text=f"{label}  {counts[key]}")

    def _populate_tree(self, packages):
        self._clear_tree()
        selected_item = None
        insert = self.tree.insert
        for i, pkg in enumerate(packages):
            row_tag = "even" if i % 2 == 0 else "odd"
            tags    = [row_tag]
            if pkg["type"]   == "System": tags.append("system")
            elif pkg["type"] == "User":   tags.append("user")
            if pkg["status"] == "Disabled": tags.append("disabled")
            item_id = insert("", "end",
                              values=(pkg["package"], pkg["type"], pkg["status"]),
                              tags=tuple(tags))
            if pkg["package"] == self.selected_package_name:
                selected_item = item_id

        if selected_item:
            self.tree.selection_set(selected_item)
            self.tree.focus(selected_item)
            self.tree.see(selected_item)
            self._update_selected_package_card(
                self._lookup_package(self.selected_package_name))
        else:
            self.tree.selection_remove(self.tree.selection())
            self.selected_package_name = None
            self._update_selected_package_card(None)

    def _clear_tree(self):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)

    def _show_table_state(self, message):
        self.table_state_label.configure(text=message)
        self.table_state_label.lift()
        self.table_state_label.place(relx=0.5, rely=0.5, anchor="center")

    def _hide_table_state(self):
        self.table_state_label.place_forget()

    def _set_filter(self, key):
        self.current_filter = key
        self._update_filter_button_styles()
        self._apply_filter_and_search()

    def _update_filter_button_styles(self):
        for key, btn in self.filter_buttons.items():
            btn.configure(
                style="SegOn.TButton" if key == self.current_filter else "Seg.TButton")

    def _sort_tree(self, column):
        if self._sort_col == column:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col     = column
            self._sort_reverse = False
        self._apply_filter_and_search()

    def _on_search_changed(self, *_):
        if self._search_after_id:
            self.root.after_cancel(self._search_after_id)
        self._search_after_id = self.root.after(180, self._apply_filter_and_search)
        self._refresh_interactive_states()

    def _clear_search(self):
        self.search_var.set("")
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, "Search packages\u2026")
        self.search_entry.configure(foreground=T4)
        self._search_placeholder = True
        self._focus_search()
        self._apply_filter_and_search()

    def _focus_search(self):
        self.search_entry.focus_set()
        if not self._search_placeholder:
            self.search_entry.selection_range(0, "end")
        return "break"

    def _handle_refresh_shortcut(self):
        if self._is_device_ready():
            self._refresh_apps()
        else:
            self._refresh_devices()
        return "break"

    def _handle_escape_shortcut(self):
        if not self._search_placeholder and self.search_var.get().strip():
            self._clear_search()
            return "break"
        return None

    # ── Selection / actions ────────────────────────────────────────────────────
    def _on_package_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            self.selected_package_name = None
            self._update_selected_package_card(None)
            self._refresh_interactive_states()
            return
        values = self.tree.item(sel[0], "values")
        self.selected_package_name = values[0]
        self._update_selected_package_card(
            self._lookup_package(self.selected_package_name))
        self._refresh_interactive_states()

    def _on_package_double_click(self, event):
        self._action_open_info()

    def _get_selected_package(self):
        if not self.selected_package_name:
            return None
        pkg = self._lookup_package(self.selected_package_name)
        if pkg:
            return pkg
        sel = self.tree.selection()
        if not sel:
            return None
        v = self.tree.item(sel[0], "values")
        return {"package": v[0], "type": v[1], "status": v[2]}

    def _update_selected_package_card(self, package):
        if not package:
            self.selection_badge_label.configure(text="None", bg=GLASS_3, fg=T4)
            self.selected_pkg_title_label.configure(text="No package selected")
            self.selected_pkg_note_label.configure(
                text="Select a package in the table to see its type, status, and actions.")
            self.pkg_type_chip.configure(text="Type: --",   bg=GLASS_3, fg=T4)
            self.pkg_status_chip.configure(text="Status: --", bg=GLASS_3, fg=T4)
            self.selection_footer_label.configure(
                text="System apps show extra confirmation before destructive actions.")
            return

        pkg_name = package["package"]
        pkg_type = package["type"]
        status   = package["status"]

        self.selection_badge_label.configure(
            text="Selected", bg=ACCENT_LIGHT, fg=ACCENT_TEXT)
        self.selected_pkg_title_label.configure(text=pkg_name)

        if pkg_type == "System":
            note    = "System app \u2014 disable or uninstall may affect device stability."
            footer  = "Use extra care. Open App Info first if unsure."
            type_bg = WARNING_LIGHT
            type_fg = WARNING_TEXT
        elif pkg_type == "User":
            note    = "User-installed app \u2014 generally safe to disable or uninstall."
            footer  = "User packages are typically reversible with fewer side effects."
            type_bg = SUCCESS_LIGHT
            type_fg = SUCCESS_TEXT
        else:
            note    = "Package type unknown. Review carefully before making changes."
            footer  = "Unknown type \u2014 the device did not classify it cleanly."
            type_bg = GLASS_3
            type_fg = T3

        if status == "Disabled":
            status_bg = WARNING_LIGHT
            status_fg = WARNING_TEXT
            note      = "Package is disabled. Enable it to restore access on the device."
        else:
            status_bg = SUCCESS_LIGHT
            status_fg = SUCCESS_TEXT

        self.selected_pkg_note_label.configure(text=note)
        self.pkg_type_chip.configure(text=f"Type: {pkg_type}", bg=type_bg, fg=type_fg)
        self.pkg_status_chip.configure(text=f"Status: {status}", bg=status_bg, fg=status_fg)
        self.selection_footer_label.configure(text=footer)

    # ── ADB action wrappers ────────────────────────────────────────────────────
    def _run_adb_task(self, working_message, task_function, command_text,
                      success_message, failure_message, refresh_apps=False):
        self._begin_job(working_message)

        def callback(result):
            self._end_job()
            if self._handle_thread_error(result, failure_message):
                return
            stdout, stderr, code, timestamp = result
            self._log_command(command_text, stdout, stderr, code, timestamp)
            if code == 0:
                if refresh_apps:
                    self._set_status(f"{success_message} Refreshing\u2026", SUCCESS)
                    self.root.after(80, self._refresh_apps)
                else:
                    self._set_status(success_message, SUCCESS)
            else:
                self._set_status(failure_message, DANGER)

        self.run_in_thread(task_function, callback)

    def _action_enable(self):
        serial  = self._get_serial()
        package = self._get_selected_package()
        if not serial or not package:
            return
        pkg_name = package["package"]
        if not messagebox.askyesno("Enable Package", f"Enable this package?\n\n{pkg_name}"):
            return
        self._run_adb_task(
            f"Enabling {pkg_name}\u2026",
            lambda: app_manager.enable_package(serial, pkg_name),
            f"adb -s {serial} shell pm enable {pkg_name}",
            f"Enabled {pkg_name}.", f"Failed to enable {pkg_name}.",
            refresh_apps=True)

    def _action_disable(self):
        serial  = self._get_serial()
        package = self._get_selected_package()
        if not serial or not package:
            return
        pkg_name = package["package"]
        if package["type"] == "System":
            msg   = (f"This is a system app. Disabling it may break phone features.\n\n"
                     f"{pkg_name}\n\nContinue?")
            title = "Disable System App"
            icon  = "warning"
        else:
            msg   = f"Disable this package?\n\n{pkg_name}"
            title = "Confirm Disable"
            icon  = "question"
        if not messagebox.askyesno(title, msg, icon=icon):
            return
        self._run_adb_task(
            f"Disabling {pkg_name}\u2026",
            lambda: app_manager.disable_package(serial, pkg_name),
            f"adb -s {serial} shell pm disable-user --user 0 {pkg_name}",
            f"Disabled {pkg_name}.", f"Failed to disable {pkg_name}.",
            refresh_apps=True)

    def _action_uninstall(self):
        serial  = self._get_serial()
        package = self._get_selected_package()
        if not serial or not package:
            return
        pkg_name = package["package"]
        if package["type"] == "System":
            msg   = (f"This may remove a system app for the current user.\n\n"
                     f"{pkg_name}\n\nContinue?")
            title = "Uninstall System App"
            icon  = "warning"
        else:
            msg   = f"Uninstall for current user?\n\n{pkg_name}"
            title = "Confirm Uninstall"
            icon  = "question"
        if not messagebox.askyesno(title, msg, icon=icon):
            return
        self._run_adb_task(
            f"Uninstalling {pkg_name}\u2026",
            lambda: app_manager.uninstall_package_for_user(serial, pkg_name),
            f"adb -s {serial} shell cmd package uninstall {pkg_name}",
            f"Uninstalled {pkg_name}.", f"Failed to uninstall {pkg_name}.",
            refresh_apps=True)

    def _action_open_info(self):
        serial  = self._get_serial()
        package = self._get_selected_package()
        if not serial or not package:
            return
        pkg_name = package["package"]
        self._run_adb_task(
            f"Opening App Info for {pkg_name}\u2026",
            lambda: app_manager.open_app_info(serial, pkg_name),
            f"adb -s {serial} shell am start "
            f"-a android.settings.APPLICATION_DETAILS_SETTINGS "
            f"-d package:{pkg_name}",
            f"Opened App Info for {pkg_name}.",
            f"Failed to open App Info for {pkg_name}.")

    def _action_copy(self):
        package = self._get_selected_package()
        if not package:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(package["package"])
        self._set_status(f"Copied {package['package']} to clipboard.", SUCCESS)

    # ── Custom command ─────────────────────────────────────────────────────────
    def _set_sample_command(self, command):
        self.custom_cmd_var.set(command)
        self.custom_cmd_entry.focus_set()
        self.custom_cmd_entry.icursor("end")

    def _run_custom_command(self):
        serial = self._get_serial()
        if not serial or not self._is_device_ready():
            messagebox.showwarning(
                "No Ready Device",
                "Please select a ready device before running shell commands.")
            return
        command = self.custom_cmd_var.get().strip()
        if not command:
            messagebox.showwarning("Empty Command",
                                   "Please enter a shell command to run.")
            return
        self._run_adb_task(
            f"Running shell command on {serial}\u2026",
            lambda: adb_manager.run_shell_command(serial, command),
            f"adb -s {serial} shell {command}",
            "Shell command finished.", "Shell command failed.")

    # ── Export ─────────────────────────────────────────────────────────────────
    def _default_export_name(self, ext):
        serial    = (self._get_serial() or "device").replace(":", "_").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"adb_packages_{serial}_{self.current_filter}_{timestamp}.{ext}"

    def _export_txt(self):
        if not self.visible_packages:
            messagebox.showinfo("Nothing to Export", "No visible packages to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=self._default_export_name("txt"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Package List as TXT")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# ADB Device Manager \u2014 Package Export\n")
                f.write(f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Device: {self._get_serial()}\n")
                f.write(f"# Filter: {self.current_filter}\n\n")
                for p in self.visible_packages:
                    f.write(f"{p['package']}  [{p['type']}]  [{p['status']}]\n")
            self._set_status(
                f"Exported {len(self.visible_packages)} packages to TXT.", SUCCESS)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))

    def _export_csv(self):
        if not self.visible_packages:
            messagebox.showinfo("Nothing to Export", "No visible packages to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=self._default_export_name("csv"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Package List as CSV")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["package_name", "type", "status"])
                for p in self.visible_packages:
                    writer.writerow([p["package"], p["type"], p["status"]])
            self._set_status(
                f"Exported {len(self.visible_packages)} packages to CSV.", SUCCESS)
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc))
