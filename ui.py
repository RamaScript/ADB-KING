"""
ui.py
PySide6 UI for ADB KING.
"""

from __future__ import annotations

import csv
import traceback
from datetime import datetime
from functools import partial

from PySide6.QtCore import QObject, QRunnable, QSettings, QThreadPool, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QPixmap, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import adb_manager
import app_manager
from app_metadata import APP_DESCRIPTION, APP_NAME, DEFAULT_THEME, resolve_logo_path


FILTER_TABS = [
    ("all", "All Apps"),
    ("user", "User Apps"),
    ("system", "System Apps"),
    ("enabled", "Enabled Apps"),
    ("disabled", "Disabled Apps"),
]

FILTER_LABELS = dict(FILTER_TABS)

LIGHT_STYLESHEET = """
QMainWindow {
    background: #eef3f9;
}
QWidget {
    background: transparent;
    color: #10233d;
    font-family: ".SF NS Text", "Segoe UI", sans-serif;
    font-size: 13px;
}
QLabel {
    background: transparent;
}
QFrame[card="true"] {
    background: rgba(255, 255, 255, 0.84);
    border: 1px solid rgba(188, 204, 223, 0.9);
    border-radius: 18px;
}
QLabel[role="title"] {
    color: #0d213a;
    font-size: 30px;
    font-weight: 700;
}
QLabel[role="logo"] {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(188, 204, 223, 0.9);
    border-radius: 20px;
    padding: 8px;
}
QLabel[role="section"] {
    color: #10233d;
    font-size: 16px;
    font-weight: 600;
}
QLabel[role="subtitle"],
QLabel[role="muted"] {
    color: #5e6c81;
}
QLabel[role="package"] {
    color: #0d213a;
    font-size: 20px;
    font-weight: 700;
}
QLabel[role="hint"] {
    color: #7c8ca3;
    font-size: 12px;
}
QLabel[badge="idle"] {
    background: rgba(236, 241, 247, 0.95);
    color: #536274;
    border: 1px solid #d6dee8;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="ok"] {
    background: rgba(232, 248, 239, 0.96);
    color: #0f7a43;
    border: 1px solid #c8ead4;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="warn"] {
    background: rgba(255, 246, 232, 0.96);
    color: #9a6500;
    border: 1px solid #f0ddb3;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="error"] {
    background: rgba(255, 241, 241, 0.96);
    color: #b42318;
    border: 1px solid #efc2be;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLineEdit, QComboBox {
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid #ccd8e6;
    border-radius: 12px;
    padding: 8px 12px;
    min-height: 18px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #1e66f5;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #ccd8e6;
    selection-background-color: #dceafe;
    selection-color: #10233d;
}
QPushButton {
    background: rgba(255, 255, 255, 0.9);
    color: #10233d;
    border: 1px solid #ccd8e6;
    border-radius: 12px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #ffffff;
    border-color: #bdd1e7;
}
QPushButton:pressed {
    background: #edf5ff;
}
QPushButton:disabled {
    background: rgba(243, 245, 248, 0.86);
    color: #a2aebd;
    border-color: #e0e7ef;
}
QPushButton[role="primary"] {
    background: #1e66f5;
    color: #ffffff;
    border: 1px solid #1e66f5;
}
QPushButton[role="primary"]:hover {
    background: #1859d7;
}
QPushButton[role="danger"] {
    background: #fff2f2;
    color: #b42318;
    border: 1px solid #efc2be;
}
QPushButton[role="success"] {
    background: #eaf8ef;
    color: #0f7a43;
    border: 1px solid #c8ead4;
}
QTabWidget::pane {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(203, 216, 231, 0.9);
    border-radius: 18px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    border: 0;
    padding: 10px 16px;
    margin-right: 4px;
    color: #5e6c81;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: rgba(255, 255, 255, 0.96);
    color: #10233d;
    border: 1px solid #d9e3ef;
    border-bottom-color: rgba(255, 255, 255, 0.96);
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}
QTableWidget {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid rgba(206, 218, 232, 0.95);
    border-radius: 16px;
    gridline-color: #eef2f7;
    selection-background-color: #dceafe;
    selection-color: #0d213a;
    alternate-background-color: #f7faff;
}
QTableWidget::item {
    padding: 10px 8px;
    border: none;
}
QHeaderView::section {
    background: rgba(246, 248, 252, 0.98);
    color: #49586d;
    border: none;
    border-bottom: 1px solid #e4eaf2;
    padding: 10px 10px;
    font-weight: 600;
}
QTextEdit {
    background: #0a1321;
    color: #dbe7f7;
    border: 1px solid #1b2940;
    border-radius: 16px;
    padding: 12px;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #c9d6e5;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QSplitter::handle {
    background: transparent;
}
QStatusBar {
    background: rgba(255, 255, 255, 0.72);
    border-top: 1px solid #d9e3ef;
}
QStatusBar::item {
    border: none;
}
"""

DARK_STYLESHEET = """
QMainWindow {
    background: #111827;
}
QWidget {
    background: transparent;
    color: #e7ecf5;
    font-family: ".SF NS Text", "Segoe UI", sans-serif;
    font-size: 13px;
}
QLabel {
    background: transparent;
}
QFrame[card="true"] {
    background: rgba(20, 29, 42, 0.88);
    border: 1px solid rgba(42, 56, 77, 0.95);
    border-radius: 18px;
}
QLabel[role="title"] {
    color: #f5f8fd;
    font-size: 30px;
    font-weight: 700;
}
QLabel[role="logo"] {
    background: rgba(23, 32, 46, 0.98);
    border: 1px solid rgba(42, 56, 77, 0.95);
    border-radius: 20px;
    padding: 8px;
}
QLabel[role="section"] {
    color: #eef3fb;
    font-size: 16px;
    font-weight: 600;
}
QLabel[role="subtitle"],
QLabel[role="muted"] {
    color: #98a7bd;
}
QLabel[role="package"] {
    color: #f5f8fd;
    font-size: 20px;
    font-weight: 700;
}
QLabel[role="hint"] {
    color: #7d90ab;
    font-size: 12px;
}
QLabel[badge="idle"] {
    background: rgba(32, 43, 60, 0.96);
    color: #b7c4d7;
    border: 1px solid #314157;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="ok"] {
    background: rgba(21, 58, 42, 0.96);
    color: #73d49f;
    border: 1px solid #23573d;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="warn"] {
    background: rgba(61, 50, 25, 0.96);
    color: #f2c86c;
    border: 1px solid #645128;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLabel[badge="error"] {
    background: rgba(69, 37, 38, 0.96);
    color: #ffaba5;
    border: 1px solid #6e373a;
    border-radius: 999px;
    padding: 5px 12px;
    font-weight: 600;
}
QLineEdit, QComboBox {
    background: rgba(26, 36, 51, 0.98);
    color: #eef3fb;
    border: 1px solid #33445d;
    border-radius: 12px;
    padding: 8px 12px;
    min-height: 18px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #7cb7ff;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #1a2433;
    border: 1px solid #33445d;
    selection-background-color: #264b74;
    selection-color: #f5f8fd;
}
QPushButton {
    background: rgba(26, 36, 51, 0.92);
    color: #eef3fb;
    border: 1px solid #33445d;
    border-radius: 12px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #202c3f;
    border-color: #47617f;
}
QPushButton:pressed {
    background: #253248;
}
QPushButton:disabled {
    background: #151d2a;
    color: #708198;
    border-color: #253246;
}
QPushButton[role="primary"] {
    background: #4d9fff;
    color: #071421;
    border: 1px solid #4d9fff;
}
QPushButton[role="primary"]:hover {
    background: #78b7ff;
}
QPushButton[role="danger"] {
    background: #382124;
    color: #ffb7b1;
    border: 1px solid #6e373a;
}
QPushButton[role="success"] {
    background: #163628;
    color: #8ee0af;
    border: 1px solid #25573f;
}
QTabWidget::pane {
    background: rgba(22, 30, 43, 0.74);
    border: 1px solid rgba(38, 50, 70, 0.92);
    border-radius: 18px;
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    border: 0;
    padding: 10px 16px;
    margin-right: 4px;
    color: #98a7bd;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: rgba(22, 30, 43, 0.98);
    color: #f5f8fd;
    border: 1px solid #263246;
    border-bottom-color: rgba(22, 30, 43, 0.98);
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
}
QTableWidget {
    background: rgba(22, 30, 43, 0.98);
    border: 1px solid rgba(38, 50, 70, 0.94);
    border-radius: 16px;
    gridline-color: #212c3f;
    selection-background-color: #264b74;
    selection-color: #f5f8fd;
    alternate-background-color: #182233;
}
QTableWidget::item {
    padding: 10px 8px;
    border: none;
}
QHeaderView::section {
    background: #1a2433;
    color: #b6c2d4;
    border: none;
    border-bottom: 1px solid #263246;
    padding: 10px 10px;
    font-weight: 600;
}
QTextEdit {
    background: #09111d;
    color: #dbe7f7;
    border: 1px solid #223146;
    border-radius: 16px;
    padding: 12px;
    font-family: "SF Mono", "Menlo", "Consolas", monospace;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #3b4c66;
    border-radius: 6px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QSplitter::handle {
    background: transparent;
}
QStatusBar {
    background: rgba(18, 24, 36, 0.78);
    border-top: 1px solid #263246;
}
QStatusBar::item {
    border: none;
}
"""


class WorkerSignals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class FunctionWorker(QRunnable):
    def __init__(self, task_function):
        super().__init__()
        self.task_function = task_function
        self.signals = WorkerSignals()

    def run(self):
        try:
            result = self.task_function()
            self.signals.result.emit(result)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
        finally:
            self.signals.finished.emit()


class ADBKingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool.globalInstance()
        self.settings = QSettings()

        self.devices = []
        self.packages = []
        self.filtered_cache = {key: [] for key, _ in FILTER_TABS}
        self.selected_serial = None
        self.selected_package_name = None
        self.busy_count = 0
        self.current_theme = DEFAULT_THEME
        self.output_collapsed = False
        self._tables_syncing = False
        self._has_shown_adb_warning = False
        self._responsive_layout_mode = None
        self._main_splitter_mode = None

        self.tables = {}
        self.tab_indices = {}
        self.device_info_labels = {}

        self.setWindowTitle(APP_NAME)
        self.resize(1460, 920)
        self.setMinimumSize(900, 640)

        self._build_ui()
        self._connect_shortcuts()
        self._restore_persisted_state()
        self._apply_theme(self.current_theme)
        self._set_device_badge("idle", "No device selected")
        self._set_activity_badge("idle", "Ready")
        self._set_device_hint("Connect your Android phone with USB debugging enabled.")
        self._set_device_info_values(
            {
                "manufacturer": "—",
                "model": "—",
                "android_version": "—",
                "sdk": "—",
                "serial": "—",
                "fingerprint": "Select a connected device to load details.",
            }
        )
        self._set_selected_package(None)
        self._append_output_message(
            "Session Started",
            "App launched successfully. Refresh devices to begin or connect a phone with USB debugging enabled.",
        )
        self._refresh_package_tables()
        self.refresh_devices()

    def _build_ui(self):
        central = QWidget()
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 18, 18, 12)
        root_layout.setSpacing(10)
        self.setCentralWidget(central)

        root_layout.addWidget(self._build_header_card())
        root_layout.addWidget(self._build_device_toolbar_card())

        self.vertical_splitter = QSplitter(Qt.Vertical)
        self.vertical_splitter.setChildrenCollapsible(False)
        root_layout.addWidget(self.vertical_splitter, 1)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(10)

        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setUsesScrollButtons(True)
        self.tab_widget.setElideMode(Qt.ElideRight)
        self.tab_widget.tabBar().setExpanding(False)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        left_layout.addWidget(self.tab_widget, 1)
        self._build_app_tabs()
        self._build_commands_tab()

        self.main_splitter.addWidget(self.left_panel)
        self.inspector_panel = self._build_inspector_panel()
        self.main_splitter.addWidget(self.inspector_panel)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes([1080, 320])

        self.vertical_splitter.addWidget(self.main_splitter)
        self.output_card = self._build_output_card()
        self.vertical_splitter.addWidget(self.output_card)
        self.vertical_splitter.setStretchFactor(0, 7)
        self.vertical_splitter.setStretchFactor(1, 1)
        self.vertical_splitter.setSizes([820, 150])

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.status_summary = QLabel("Ready")
        self.status_summary.setProperty("role", "muted")
        status_bar.addPermanentWidget(self.status_summary)

        self._update_splitter_orientation(force=True)
        self._update_responsive_layouts(force=True)

    def _build_header_card(self):
        card = self._create_card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        logo_label = self._create_brand_logo_label()
        if logo_label is not None:
            layout.addWidget(logo_label, 0, Qt.AlignTop)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(2)

        title = QLabel(APP_NAME)
        title.setProperty("role", "title")
        title_column.addWidget(title)

        subtitle = QLabel(APP_DESCRIPTION)
        subtitle.setProperty("role", "subtitle")
        subtitle.setWordWrap(True)
        title_column.addWidget(subtitle)

        layout.addLayout(title_column, 1)

        badge_column = QVBoxLayout()
        badge_column.setContentsMargins(0, 0, 0, 0)
        badge_column.setSpacing(4)

        self.activity_badge = QLabel("Ready")
        self.activity_badge.setAlignment(Qt.AlignCenter)
        self.activity_badge.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        badge_column.addWidget(self.activity_badge, 0, Qt.AlignRight)

        badge_hint = QLabel("Threaded ADB tasks keep the UI responsive.")
        badge_hint.setProperty("role", "hint")
        badge_hint.setAlignment(Qt.AlignRight)
        badge_column.addWidget(badge_hint)

        layout.addLayout(badge_column)
        return card

    def _create_brand_logo_label(self):
        logo_path = resolve_logo_path()
        if not logo_path:
            return None

        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            return None

        label = QLabel()
        label.setProperty("role", "logo")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedSize(76, 76)
        label.setPixmap(
            pixmap.scaled(
                56,
                56,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        return label

    def _build_device_toolbar_card(self):
        card = self._create_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.device_controls_grid = QGridLayout()
        self.device_controls_grid.setContentsMargins(0, 0, 0, 0)
        self.device_controls_grid.setHorizontalSpacing(10)
        self.device_controls_grid.setVerticalSpacing(10)

        self.device_label = QLabel("Device")
        self.device_label.setProperty("role", "muted")

        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        self.refresh_devices_button = QPushButton("Refresh Devices")
        self.refresh_devices_button.setProperty("role", "primary")
        self.refresh_devices_button.clicked.connect(self.refresh_devices)

        self.device_badge = QLabel("No device selected")
        self.device_badge.setAlignment(Qt.AlignCenter)
        self.device_badge.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

        self.theme_label = QLabel("Theme")
        self.theme_label.setProperty("role", "muted")

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.currentTextChanged.connect(self._apply_theme)
        self.theme_combo.setMaximumWidth(120)

        layout.addLayout(self.device_controls_grid)

        self.device_hint_label = QLabel("")
        self.device_hint_label.setProperty("role", "muted")
        self.device_hint_label.setWordWrap(True)
        layout.addWidget(self.device_hint_label)

        self.apps_toolbar_card = QWidget()
        apps_layout = QVBoxLayout(self.apps_toolbar_card)
        apps_layout.setContentsMargins(0, 6, 0, 0)
        apps_layout.setSpacing(10)

        apps_header = QHBoxLayout()
        apps_header.setContentsMargins(0, 0, 0, 0)
        apps_header.setSpacing(8)

        apps_title = QLabel("Applications")
        apps_title.setProperty("role", "section")
        apps_header.addWidget(apps_title)
        apps_header.addStretch(1)

        self.package_summary_label = QLabel("No packages loaded yet")
        self.package_summary_label.setProperty("role", "muted")
        apps_header.addWidget(self.package_summary_label)
        apps_layout.addLayout(apps_header)

        self.apps_controls_grid = QGridLayout()
        self.apps_controls_grid.setContentsMargins(0, 0, 0, 0)
        self.apps_controls_grid.setHorizontalSpacing(10)
        self.apps_controls_grid.setVerticalSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search package name")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._refresh_package_tables)

        self.clear_search_button = QPushButton("Clear")
        self.clear_search_button.clicked.connect(self.search_input.clear)

        self.refresh_apps_button = QPushButton("Refresh Apps")
        self.refresh_apps_button.setProperty("role", "primary")
        self.refresh_apps_button.clicked.connect(self.refresh_apps)

        self.export_csv_button = QPushButton("CSV")
        self.export_csv_button.clicked.connect(partial(self.export_visible_packages, "csv"))

        self.export_txt_button = QPushButton("TXT")
        self.export_txt_button.clicked.connect(partial(self.export_visible_packages, "txt"))
        self.package_summary_label.setWordWrap(True)

        apps_layout.addLayout(self.apps_controls_grid)
        layout.addWidget(self.apps_toolbar_card)
        return card

    def _build_app_tabs(self):
        for key, label in FILTER_TABS:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(0)

            table = self._create_package_table()
            table.itemSelectionChanged.connect(partial(self._handle_table_selection, key))
            page_layout.addWidget(table)

            index = self.tab_widget.addTab(page, label)
            self.tables[key] = table
            self.tab_indices[key] = index

    def _build_commands_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        header = QLabel("Custom Shell Command")
        header.setProperty("role", "section")
        layout.addWidget(header)

        description = QLabel(
            "Run advanced ADB shell commands on the selected device. Keep this for power-user workflows like dumpsys, settings, and package diagnostics."
        )
        description.setProperty("role", "muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("pm list packages")
        self.command_input.returnPressed.connect(self.run_custom_shell_command)
        self.command_input.textChanged.connect(self._refresh_interactivity)
        row.addWidget(self.command_input, 1)

        self.run_command_button = QPushButton("Run Shell Command")
        self.run_command_button.setProperty("role", "primary")
        self.run_command_button.clicked.connect(self.run_custom_shell_command)
        row.addWidget(self.run_command_button)
        layout.addLayout(row)

        notes = QLabel(
            "Examples: pm list packages, settings get global device_name, dumpsys package com.example.app"
        )
        notes.setProperty("role", "muted")
        notes.setWordWrap(True)
        layout.addWidget(notes)

        layout.addStretch(1)

        index = self.tab_widget.addTab(page, "Commands")
        self.tab_indices["commands"] = index

    def _build_inspector_panel(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        self.package_card = self._create_card()
        package_layout = QVBoxLayout(self.package_card)
        package_layout.setContentsMargins(16, 16, 16, 16)
        package_layout.setSpacing(10)

        package_header = QHBoxLayout()
        package_header.setContentsMargins(0, 0, 0, 0)
        package_header.setSpacing(8)

        package_title = QLabel("Selected Package")
        package_title.setProperty("role", "section")
        package_header.addWidget(package_title)
        package_header.addStretch(1)

        self.actions_context_label = QLabel("Select an app to manage it.")
        self.actions_context_label.setProperty("role", "hint")
        self.actions_context_label.setWordWrap(True)
        package_header.addWidget(self.actions_context_label)
        package_layout.addLayout(package_header)

        self.package_name_label = QLabel("No package selected")
        self.package_name_label.setProperty("role", "package")
        self.package_name_label.setWordWrap(True)
        package_layout.addWidget(self.package_name_label)

        self.package_type_label = QLabel("Type: —")
        self.package_type_label.setProperty("role", "muted")
        package_layout.addWidget(self.package_type_label)

        self.package_status_label = QLabel("Status: —")
        self.package_status_label.setProperty("role", "muted")
        package_layout.addWidget(self.package_status_label)

        self.package_help_label = QLabel("Select an app from any package tab to see context here.")
        self.package_help_label.setProperty("role", "muted")
        self.package_help_label.setWordWrap(True)
        package_layout.addWidget(self.package_help_label)
        scroll_layout.addWidget(self.package_card)

        self.actions_card = self._create_card()
        actions_layout = QVBoxLayout(self.actions_card)
        actions_layout.setContentsMargins(16, 16, 16, 16)
        actions_layout.setSpacing(12)

        actions_title = QLabel("Quick Actions")
        actions_title.setProperty("role", "section")
        actions_layout.addWidget(actions_title)

        actions_grid = QGridLayout()
        actions_grid.setContentsMargins(0, 0, 0, 0)
        actions_grid.setHorizontalSpacing(10)
        actions_grid.setVerticalSpacing(10)

        self.disable_button = QPushButton("Disable App")
        self.disable_button.setProperty("role", "danger")
        self.disable_button.clicked.connect(partial(self._run_package_action, "disable"))
        actions_grid.addWidget(self.disable_button, 0, 0)

        self.enable_button = QPushButton("Enable App")
        self.enable_button.setProperty("role", "success")
        self.enable_button.clicked.connect(partial(self._run_package_action, "enable"))
        actions_grid.addWidget(self.enable_button, 0, 1)

        self.app_info_button = QPushButton("Open App Info")
        self.app_info_button.clicked.connect(partial(self._run_package_action, "open_info"))
        actions_grid.addWidget(self.app_info_button, 1, 0)

        self.copy_name_button = QPushButton("Copy Package Name")
        self.copy_name_button.clicked.connect(self.copy_selected_package_name)
        actions_grid.addWidget(self.copy_name_button, 1, 1)

        self.uninstall_button = QPushButton("Uninstall for Current User")
        self.uninstall_button.setProperty("role", "danger")
        self.uninstall_button.clicked.connect(partial(self._run_package_action, "uninstall"))
        actions_grid.addWidget(self.uninstall_button, 2, 0, 1, 2)

        actions_layout.addLayout(actions_grid)

        actions_hint = QLabel(
            "Disabling or uninstalling system apps may affect phone stability. Review the package type before continuing."
        )
        actions_hint.setProperty("role", "hint")
        actions_hint.setWordWrap(True)
        actions_layout.addWidget(actions_hint)
        scroll_layout.addWidget(self.actions_card)

        device_card = self._create_card()
        device_layout = QVBoxLayout(device_card)
        device_layout.setContentsMargins(16, 16, 16, 16)
        device_layout.setSpacing(12)

        device_title = QLabel("Device Overview")
        device_title.setProperty("role", "section")
        device_layout.addWidget(device_title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        device_rows = [
            ("manufacturer", "Manufacturer"),
            ("model", "Model"),
            ("android_version", "Android Version"),
            ("sdk", "SDK"),
            ("serial", "Serial"),
        ]
        for row_index, (key, label_text) in enumerate(device_rows):
            label = QLabel(label_text)
            label.setProperty("role", "muted")
            value = QLabel("—")
            value.setWordWrap(True)
            self.device_info_labels[key] = value
            grid.addWidget(label, row_index, 0, Qt.AlignTop)
            grid.addWidget(value, row_index, 1)

        fingerprint_label = QLabel("Build Fingerprint")
        fingerprint_label.setProperty("role", "muted")
        self.device_info_labels["fingerprint"] = QLabel("—")
        self.device_info_labels["fingerprint"].setWordWrap(True)
        grid.addWidget(fingerprint_label, len(device_rows), 0, Qt.AlignTop)
        grid.addWidget(self.device_info_labels["fingerprint"], len(device_rows), 1)

        device_layout.addLayout(grid)
        scroll_layout.addWidget(device_card)
        scroll_layout.addStretch(1)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return container

    def _build_output_card(self):
        card = self._create_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        title = QLabel("Command Output")
        title.setProperty("role", "section")
        header_row.addWidget(title)

        header_row.addStretch(1)

        self.output_toggle_button = QPushButton("Collapse")
        self.output_toggle_button.clicked.connect(self._toggle_output_panel)
        header_row.addWidget(self.output_toggle_button)

        clear_button = QPushButton("Clear Output")
        clear_button.clicked.connect(self.output_text_clear)
        header_row.addWidget(clear_button)

        layout.addLayout(header_row)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(96)
        layout.addWidget(self.output_text, 1)
        return card

    def _toggle_output_panel(self):
        self.output_collapsed = not self.output_collapsed
        self.output_text.setVisible(not self.output_collapsed)
        self.output_toggle_button.setText("Expand" if self.output_collapsed else "Collapse")
        if self.output_collapsed:
            self.vertical_splitter.setSizes([max(self.height() - 110, 560), 56])
        else:
            self.vertical_splitter.setSizes([max(self.height() - 240, 520), 180])

    def _create_card(self):
        card = QFrame()
        card.setProperty("card", "true")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        return card

    def _create_package_table(self):
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Package Name", "Type", "Status"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setFocusPolicy(Qt.NoFocus)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setSortingEnabled(False)
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        return table

    def _connect_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search_input.setFocus)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.refresh_apps)
        QShortcut(QKeySequence("F5"), self, activated=self.refresh_devices)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_splitter_orientation()
        self._update_responsive_layouts()

    def closeEvent(self, event):
        self.settings.setValue("ui/theme", self.current_theme)
        self.settings.setValue("ui/output_collapsed", self.output_collapsed)
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("window/maximized", self.isMaximized())
        super().closeEvent(event)

    def _update_splitter_orientation(self, force=False):
        mode = "stacked" if self.width() < 1220 else "side-by-side"
        if not force and mode == self._main_splitter_mode:
            return

        self._main_splitter_mode = mode
        if mode == "stacked":
            self.main_splitter.setOrientation(Qt.Vertical)
            self.main_splitter.setSizes([760, 360])
        else:
            self.main_splitter.setOrientation(Qt.Horizontal)
            self.main_splitter.setSizes([1080, 320])

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)

    def _reset_grid_stretch(self, layout, column_count):
        for column in range(column_count):
            layout.setColumnStretch(column, 0)

    def _update_responsive_layouts(self, force=False):
        if self.width() < 1080:
            mode = "compact"
        elif self.width() < 1440:
            mode = "medium"
        else:
            mode = "wide"

        if not force and mode == self._responsive_layout_mode:
            return

        self._responsive_layout_mode = mode
        self._clear_layout(self.device_controls_grid)
        self._clear_layout(self.apps_controls_grid)
        self._reset_grid_stretch(self.device_controls_grid, 6)
        self._reset_grid_stretch(self.apps_controls_grid, 5)

        if mode == "wide":
            self.device_controls_grid.addWidget(self.device_label, 0, 0)
            self.device_controls_grid.addWidget(self.device_combo, 0, 1)
            self.device_controls_grid.addWidget(self.refresh_devices_button, 0, 2)
            self.device_controls_grid.addWidget(self.device_badge, 0, 3)
            self.device_controls_grid.addWidget(self.theme_label, 0, 4)
            self.device_controls_grid.addWidget(self.theme_combo, 0, 5)
            self.device_controls_grid.setColumnStretch(1, 1)

            self.apps_controls_grid.addWidget(self.search_input, 0, 0)
            self.apps_controls_grid.addWidget(self.clear_search_button, 0, 1)
            self.apps_controls_grid.addWidget(self.refresh_apps_button, 0, 2)
            self.apps_controls_grid.addWidget(self.export_csv_button, 0, 3)
            self.apps_controls_grid.addWidget(self.export_txt_button, 0, 4)
            self.apps_controls_grid.setColumnStretch(0, 1)
            return

        if mode == "medium":
            self.device_controls_grid.addWidget(self.device_label, 0, 0)
            self.device_controls_grid.addWidget(self.device_combo, 0, 1, 1, 3)
            self.device_controls_grid.addWidget(self.refresh_devices_button, 0, 4)
            self.device_controls_grid.addWidget(self.device_badge, 1, 0, 1, 3)
            self.device_controls_grid.addWidget(self.theme_label, 1, 3)
            self.device_controls_grid.addWidget(self.theme_combo, 1, 4)
            self.device_controls_grid.setColumnStretch(1, 1)

            self.apps_controls_grid.addWidget(self.search_input, 0, 0, 1, 4)
            self.apps_controls_grid.addWidget(self.clear_search_button, 1, 0)
            self.apps_controls_grid.addWidget(self.refresh_apps_button, 1, 1)
            self.apps_controls_grid.addWidget(self.export_csv_button, 1, 2)
            self.apps_controls_grid.addWidget(self.export_txt_button, 1, 3)
            self.apps_controls_grid.setColumnStretch(0, 1)
            return

        self.device_controls_grid.addWidget(self.device_label, 0, 0)
        self.device_controls_grid.addWidget(self.theme_label, 0, 1)
        self.device_controls_grid.addWidget(self.device_combo, 1, 0, 1, 2)
        self.device_controls_grid.addWidget(self.refresh_devices_button, 2, 0)
        self.device_controls_grid.addWidget(self.theme_combo, 2, 1)
        self.device_controls_grid.addWidget(self.device_badge, 3, 0, 1, 2)
        self.device_controls_grid.setColumnStretch(0, 1)

        self.apps_controls_grid.addWidget(self.search_input, 0, 0, 1, 2)
        self.apps_controls_grid.addWidget(self.clear_search_button, 1, 0)
        self.apps_controls_grid.addWidget(self.refresh_apps_button, 1, 1)
        self.apps_controls_grid.addWidget(self.export_csv_button, 2, 0)
        self.apps_controls_grid.addWidget(self.export_txt_button, 2, 1)
        self.apps_controls_grid.setColumnStretch(0, 1)

    def _read_bool_setting(self, key, default=False):
        value = self.settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _restore_persisted_state(self):
        theme_name = self.settings.value("ui/theme", DEFAULT_THEME)
        if theme_name in {"Light", "Dark"}:
            self.current_theme = theme_name

        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(self.current_theme)
        self.theme_combo.blockSignals(False)

        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)

        if self._read_bool_setting("window/maximized", False):
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

        self._update_splitter_orientation(force=True)
        self._update_responsive_layouts(force=True)

        if self._read_bool_setting("ui/output_collapsed", False):
            self._toggle_output_panel()

    def _apply_theme(self, theme_name):
        if theme_name not in {"Light", "Dark"}:
            theme_name = DEFAULT_THEME
        self.current_theme = theme_name
        stylesheet = LIGHT_STYLESHEET if theme_name == "Light" else DARK_STYLESHEET
        self.setStyleSheet(stylesheet)

    def _set_badge(self, widget, badge_type, text):
        widget.setProperty("badge", badge_type)
        widget.setText(text)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _set_device_badge(self, badge_type, text):
        self._set_badge(self.device_badge, badge_type, text)

    def _set_activity_badge(self, badge_type, text):
        self._set_badge(self.activity_badge, badge_type, text)

    def _set_device_hint(self, text):
        self.device_hint_label.setText(text)

    def _set_status_message(self, text):
        self.statusBar().showMessage(text, 5000)
        self.status_summary.setText(text)

    def _begin_task(self, text):
        self.busy_count += 1
        self._set_activity_badge("warn", text)
        self._set_status_message(text)
        self._refresh_interactivity()

    def _finish_task(self):
        self.busy_count = max(0, self.busy_count - 1)
        if self.busy_count == 0:
            self._set_activity_badge("ok", "Done")
            self._set_status_message("Done")
        self._refresh_interactivity()

    def _refresh_interactivity(self):
        busy = self.busy_count > 0
        device_ready = self._selected_device_ready()
        current_key = self._current_app_tab_key()
        current_package = self._current_package_data()

        self.refresh_devices_button.setEnabled(not busy)
        self.device_combo.setEnabled(not busy)
        self.refresh_apps_button.setEnabled(device_ready and not busy and current_key is not None)
        self.export_csv_button.setEnabled(device_ready and not busy and current_key is not None and bool(self.filtered_cache.get(current_key)))
        self.export_txt_button.setEnabled(device_ready and not busy and current_key is not None and bool(self.filtered_cache.get(current_key)))
        self.run_command_button.setEnabled(device_ready and not busy and bool(self.command_input.text().strip()))

        can_use_package_actions = device_ready and not busy and current_key is not None and current_package is not None
        self.copy_name_button.setEnabled(can_use_package_actions)
        self.app_info_button.setEnabled(can_use_package_actions)
        self.disable_button.setEnabled(can_use_package_actions and current_package["status"] == "Enabled")
        self.enable_button.setEnabled(can_use_package_actions and current_package["status"] == "Disabled")
        self.uninstall_button.setEnabled(can_use_package_actions)
        self.clear_search_button.setEnabled(bool(self.search_input.text()))

        self.apps_toolbar_card.setVisible(current_key is not None)
        self.package_card.setVisible(current_key is not None)
        self.actions_card.setVisible(current_key is not None)

    def run_in_thread(self, task_function, callback_function=None, status_text="Working...", error_callback=None):
        self._begin_task(status_text)
        worker = FunctionWorker(task_function)

        if callback_function is not None:
            worker.signals.result.connect(callback_function)

        def handle_error(error_text):
            if error_callback is not None:
                error_callback(error_text)
            else:
                self._append_output_block(
                    "Unexpected Error",
                    "Internal worker execution",
                    "",
                    error_text,
                    False,
                    self._timestamp_now(),
                )
                QMessageBox.critical(self, "Unexpected Error", error_text)

        worker.signals.error.connect(handle_error)
        worker.signals.finished.connect(self._finish_task)
        self.thread_pool.start(worker)

    def refresh_devices(self):
        def task():
            adb_manager.adb_start_server()
            devices, error = adb_manager.list_devices()
            return {"devices": devices, "error": error}

        self.run_in_thread(task, self._on_devices_loaded, status_text="Refreshing devices...")

    def _on_devices_loaded(self, payload):
        devices = payload["devices"]
        error = payload["error"]
        self.devices = devices

        stdout_lines = ["List of devices attached"]
        for device in devices:
            stdout_lines.append(f"{device['serial']}\t{device['status']}")
        if not devices:
            stdout_lines.append("(no devices found)")

        success = "ADB not found" not in error if error else True
        self._append_output_block(
            "Device Scan",
            "adb devices",
            "\n".join(stdout_lines),
            error,
            success,
            self._timestamp_now(),
        )

        self._populate_device_combo()

        if error and "ADB not found" in error:
            self._set_device_badge("error", "ADB not found")
            self._set_device_hint(error)
            self._clear_device_session()
            if not self._has_shown_adb_warning:
                self._has_shown_adb_warning = True
                QMessageBox.warning(self, "ADB Not Found", error)
            return

        if not devices:
            self._set_device_badge("warn", "No device connected")
            self._set_device_hint("No Android device connected. Connect phone with USB and enable USB debugging.")
            self._clear_device_session()
            return

        ready_count = len([device for device in devices if device["status"] == "device"])
        if ready_count > 1 and not self.selected_serial:
            self._set_device_badge("idle", "Choose a device")
            self._set_device_hint("Multiple devices detected. Select which device you want to manage.")
        elif ready_count == 1 and len(devices) > 1 and not self.selected_serial:
            self._set_device_badge("idle", "Choose a device")
            self._set_device_hint("Multiple entries detected. Select the device with status 'device' to continue.")

    def _populate_device_combo(self):
        previous_serial = self.selected_serial
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("Select a device", None)

        selected_index = 0
        for idx, device in enumerate(self.devices, start=1):
            label = f"{device['serial']} ({device['status']})"
            self.device_combo.addItem(label, device)
            if previous_serial and device["serial"] == previous_serial and device["status"] == "device":
                selected_index = idx

        if selected_index == 0 and len(self.devices) == 1 and self.devices[0]["status"] == "device":
            selected_index = 1

        self.device_combo.setCurrentIndex(selected_index)
        self.device_combo.blockSignals(False)

        if selected_index > 0:
            self._on_device_changed(selected_index)
        else:
            self._on_device_changed(0)

    def _on_device_changed(self, index):
        device = self.device_combo.itemData(index)
        if not device:
            self.selected_serial = None
            if not self.devices:
                self._set_device_badge("warn", "No device connected")
                self._set_device_hint("No Android device connected. Connect phone with USB and enable USB debugging.")
            else:
                self._set_device_badge("idle", "Select a device")
                self._set_device_hint("Select a connected device before running app actions.")
            self._clear_device_session()
            return

        status = device["status"]
        serial = device["serial"]
        if status != "device":
            self.selected_serial = None
            if status == "unauthorized":
                self._set_device_badge("warn", "Unauthorized")
                self._set_device_hint("Device unauthorized. Please allow USB debugging popup on your phone.")
            elif status == "offline":
                self._set_device_badge("warn", "Offline")
                self._set_device_hint("Device offline. Reconnect the cable or wake the phone screen, then refresh.")
            else:
                self._set_device_badge("error", status.title())
                self._set_device_hint(f"Device status is '{status}'. Only devices with status 'device' can be managed.")
            self._clear_device_session()
            return

        self.selected_serial = serial
        self._set_device_badge("ok", f"Connected: {serial}")
        self._set_device_hint("Loading device information and installed packages...")
        self._load_device(serial)

    def _load_device(self, serial):
        self._set_device_info_values(
            {
                "manufacturer": "Loading...",
                "model": "Loading...",
                "android_version": "Loading...",
                "sdk": "Loading...",
                "serial": serial,
                "fingerprint": "Loading...",
            }
        )
        self.packages = []
        self.selected_package_name = None
        self._set_selected_package(None)
        self._refresh_package_tables()

        def info_task():
            return {"serial": serial, "info": adb_manager.get_device_info(serial)}

        def apps_task():
            packages, error = app_manager.classify_packages(serial)
            return {"serial": serial, "packages": packages, "error": error}

        self.run_in_thread(info_task, self._on_device_info_loaded, status_text="Loading device information...")
        self.run_in_thread(apps_task, self._on_packages_loaded, status_text="Loading apps...")

    def _on_device_info_loaded(self, payload):
        serial = payload["serial"]
        info = payload["info"]
        if serial != self.selected_serial:
            return

        self._set_device_info_values(info)
        self._set_device_hint(f"Managing device {serial}.")

        stdout = "\n".join(
            [
                f"Manufacturer: {info.get('manufacturer', 'N/A')}",
                f"Model: {info.get('model', 'N/A')}",
                f"Android: {info.get('android_version', 'N/A')}",
                f"SDK: {info.get('sdk', 'N/A')}",
                f"Fingerprint: {info.get('fingerprint', 'N/A')}",
            ]
        )
        self._append_output_block(
            "Device Information",
            f"adb -s {serial} shell getprop ...",
            stdout,
            "",
            True,
            self._timestamp_now(),
        )

    def _on_packages_loaded(self, payload):
        serial = payload["serial"]
        packages = payload["packages"]
        error = payload["error"]
        if serial != self.selected_serial:
            return

        self.packages = packages
        self._refresh_package_tables()

        stderr = error or ""
        success = bool(packages) or not stderr
        stdout = f"{len(packages)} packages loaded"
        self._append_output_block(
            "Package Scan",
            f"adb -s {serial} shell pm list packages ...",
            stdout,
            stderr,
            success,
            self._timestamp_now(),
        )

        if stderr and not packages:
            self._set_device_hint(stderr)
        elif not packages:
            self._set_device_hint("No packages were returned by the device.")
        else:
            self._set_device_hint(f"Loaded {len(packages)} packages from device {serial}.")

    def refresh_apps(self):
        serial = self._require_ready_device()
        if not serial:
            return

        def task():
            packages, error = app_manager.classify_packages(serial)
            return {"serial": serial, "packages": packages, "error": error}

        self.run_in_thread(task, self._on_packages_loaded, status_text="Refreshing apps...")

    def _set_device_info_values(self, info):
        values = {
            "manufacturer": info.get("manufacturer", "—"),
            "model": info.get("model", "—"),
            "android_version": info.get("android_version", "—"),
            "sdk": info.get("sdk", "—"),
            "serial": info.get("serial", "—"),
            "fingerprint": info.get("fingerprint", "—"),
        }
        for key, value in values.items():
            self.device_info_labels[key].setText(str(value or "—"))

    def _clear_device_session(self):
        self.packages = []
        self.selected_package_name = None
        self._set_device_info_values(
            {
                "manufacturer": "—",
                "model": "—",
                "android_version": "—",
                "sdk": "—",
                "serial": "—",
                "fingerprint": "Select a connected device to load details.",
            }
        )
        self._set_selected_package(None)
        self._refresh_package_tables()

    def _filtered_packages(self, key):
        items = list(self.packages)
        if key == "user":
            items = [item for item in items if item["type"] == "User"]
        elif key == "system":
            items = [item for item in items if item["type"] == "System"]
        elif key == "enabled":
            items = [item for item in items if item["status"] == "Enabled"]
        elif key == "disabled":
            items = [item for item in items if item["status"] == "Disabled"]

        query = self.search_input.text().strip().lower()
        if query:
            items = [item for item in items if query in item["package"].lower()]
        return items

    def _refresh_package_tables(self):
        self._tables_syncing = True
        current_key = self._current_app_tab_key()
        for key, label in FILTER_TABS:
            rows = self._filtered_packages(key)
            self.filtered_cache[key] = rows
            self._populate_table(self.tables[key], rows)
            self.tab_widget.setTabText(self.tab_indices[key], f"{label} ({len(rows)})")
        self._tables_syncing = False

        self._restore_current_selection(current_key)
        self._update_package_summary()
        self._refresh_interactivity()

    def _populate_table(self, table, rows):
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for row_index, package in enumerate(rows):
            package_item = QTableWidgetItem(package["package"])
            package_item.setData(Qt.UserRole, package)
            type_item = QTableWidgetItem(package["type"])
            status_item = QTableWidgetItem(package["status"])

            package_item.setFlags(package_item.flags() & ~Qt.ItemIsEditable)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)

            table.setItem(row_index, 0, package_item)
            table.setItem(row_index, 1, type_item)
            table.setItem(row_index, 2, status_item)
        table.blockSignals(False)

    def _restore_current_selection(self, current_key):
        if current_key is None:
            self._refresh_interactivity()
            return

        if self.selected_package_name and self._select_package_in_table(current_key, self.selected_package_name):
            return

        table = self.tables[current_key]
        if table.rowCount() > 0:
            table.selectRow(0)
            self._handle_table_selection(current_key)
        else:
            self._set_selected_package(None)

    def _select_package_in_table(self, key, package_name):
        table = self.tables[key]
        for row_index in range(table.rowCount()):
            item = table.item(row_index, 0)
            if item and item.text() == package_name:
                table.selectRow(row_index)
                table.scrollToItem(item)
                self._handle_table_selection(key)
                return True
        return False

    def _handle_table_selection(self, key):
        if self._tables_syncing or key != self._current_app_tab_key():
            return

        self._set_selected_package(self._current_package_data())

    def _set_selected_package(self, package):
        if not package:
            self.selected_package_name = None
            self.package_name_label.setText("No package selected")
            self.package_type_label.setText("Type: —")
            self.package_status_label.setText("Status: —")
            self.package_help_label.setText("Select an app from any package tab to see context here.")
            self.actions_context_label.setText("Select an app to manage it.")
        else:
            self.selected_package_name = package["package"]
            self.package_name_label.setText(package["package"])
            self.package_type_label.setText(f"Type: {package['type']}")
            self.package_status_label.setText(f"Status: {package['status']}")
            self.package_help_label.setText("Review the app type and status before running package actions.")
            self.actions_context_label.setText(package["package"])
        self._refresh_interactivity()

    def _current_package_data(self):
        key = self._current_app_tab_key()
        if key is None:
            return None
        table = self.tables[key]
        selection = table.selectionModel()
        if not selection or not selection.hasSelection():
            return None
        row = selection.selectedRows()[0].row()
        item = table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _current_app_tab_key(self):
        current_index = self.tab_widget.currentIndex()
        for key, index in self.tab_indices.items():
            if index == current_index:
                return key if key != "commands" else None
        return None

    def _on_tab_changed(self, _index):
        current_key = self._current_app_tab_key()
        if current_key is not None:
            if self.selected_package_name:
                self._select_package_in_table(current_key, self.selected_package_name)
            else:
                self._handle_table_selection(current_key)
        self._update_package_summary()
        self._refresh_interactivity()

    def _update_package_summary(self):
        current_key = self._current_app_tab_key()
        if current_key is None:
            self.package_summary_label.setText("Advanced shell commands for the selected device")
            return
        visible_count = len(self.filtered_cache.get(current_key, []))
        total_count = len(self.packages)
        self.package_summary_label.setText(f"{visible_count} visible of {total_count} total packages")

    def _require_ready_device(self):
        if not self._selected_device_ready():
            QMessageBox.information(
                self,
                "Select a Device",
                "Select a connected Android device with status 'device' before running this action.",
            )
            return None
        return self.selected_serial

    def _selected_device_ready(self):
        return bool(self.selected_serial)

    def _run_package_action(self, action_name):
        serial = self._require_ready_device()
        if not serial:
            return

        package = self._current_package_data()
        if not package:
            QMessageBox.information(self, "Select an App", "Select a package from the app list first.")
            return

        if not self._confirm_action(action_name, package):
            return

        commands = {
            "disable": (
                "Disable App",
                f"adb -s {serial} shell pm disable-user --user 0 {package['package']}",
                lambda: app_manager.disable_package(serial, package["package"]),
                True,
            ),
            "enable": (
                "Enable App",
                f"adb -s {serial} shell pm enable {package['package']}",
                lambda: app_manager.enable_package(serial, package["package"]),
                True,
            ),
            "uninstall": (
                "Uninstall for Current User",
                f"adb -s {serial} shell cmd package uninstall {package['package']}",
                lambda: app_manager.uninstall_package_for_user(serial, package["package"]),
                True,
            ),
            "open_info": (
                "Open App Info",
                f"adb -s {serial} shell am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:{package['package']}",
                lambda: app_manager.open_app_info(serial, package["package"]),
                False,
            ),
        }

        title, command, task_function, refresh_after = commands[action_name]

        def callback(result):
            success = self._log_command_tuple(title, command, result)
            if success and refresh_after:
                self.refresh_apps()

        self.run_in_thread(task_function, callback, status_text=f"{title}...")

    def _confirm_action(self, action_name, package):
        package_name = package["package"]
        package_type = package["type"]

        if action_name == "disable":
            if package_type == "System":
                message = "This is a system app. Disabling it may break phone features. Continue?"
            else:
                message = f"Disable '{package_name}' on the selected device?"
            title = "Confirm Disable"
        elif action_name == "uninstall":
            if package_type == "System":
                message = "This may remove a system app for the current user. It may affect phone stability. Continue?"
            else:
                message = f"Uninstall '{package_name}' for the current user on the selected device?"
            title = "Confirm Uninstall"
        elif action_name == "enable":
            message = f"Enable '{package_name}' on the selected device?"
            title = "Confirm Enable"
        else:
            message = f"Open the app info screen for '{package_name}' on the device?"
            title = "Open App Info"

        answer = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def run_custom_shell_command(self):
        serial = self._require_ready_device()
        if not serial:
            return

        command_text = self.command_input.text().strip()
        if not command_text:
            QMessageBox.information(self, "Empty Command", "Enter an ADB shell command before running it.")
            return

        command = f"adb -s {serial} shell {command_text}"

        def task():
            return adb_manager.run_shell_command(serial, command_text, timeout=60)

        def callback(result):
            self._log_command_tuple("Custom Shell Command", command, result)

        self.run_in_thread(task, callback, status_text="Running command...")

    def copy_selected_package_name(self):
        package = self._current_package_data()
        if not package:
            QMessageBox.information(self, "Select an App", "Select a package before copying its name.")
            return
        QGuiApplication.clipboard().setText(package["package"])
        self._set_status_message(f"Copied package name: {package['package']}")

    def export_visible_packages(self, export_format):
        current_key = self._current_app_tab_key()
        if current_key is None:
            QMessageBox.information(self, "Switch Tabs", "Export is available from the app list tabs.")
            return

        rows = self.filtered_cache.get(current_key, [])
        if not rows:
            QMessageBox.information(self, "Nothing to Export", "There are no visible packages to export right now.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{current_key}_apps_{timestamp}.{export_format}"

        if export_format == "csv":
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Visible Packages as CSV",
                default_name,
                "CSV Files (*.csv)",
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Visible Packages as TXT",
                default_name,
                "Text Files (*.txt)",
            )

        if not file_path:
            return

        try:
            if export_format == "csv":
                with open(file_path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["package_name", "type", "status"])
                    for row in rows:
                        writer.writerow([row["package"], row["type"], row["status"]])
            else:
                with open(file_path, "w", encoding="utf-8") as handle:
                    handle.write(f"{FILTER_LABELS[current_key]}\n")
                    handle.write("=" * len(FILTER_LABELS[current_key]))
                    handle.write("\n\n")
                    for row in rows:
                        handle.write(f"{row['package']} | {row['type']} | {row['status']}\n")
            self._set_status_message(f"Exported {len(rows)} packages to {file_path}")
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", f"Could not export file:\n{exc}")

    def _log_command_tuple(self, title, command, result_tuple):
        stdout, stderr, return_code, timestamp = result_tuple
        success = self._command_succeeded(stdout, stderr, return_code)
        self._append_output_block(title, command, stdout, stderr, success, timestamp)
        if not success:
            friendly_error = stderr or stdout or "The command failed."
            QMessageBox.warning(self, title, friendly_error)
        return success

    def _command_succeeded(self, stdout, stderr, return_code):
        if return_code != 0:
            return False
        haystack = f"{stdout}\n{stderr}".lower()
        for marker in ["failure", "error:", "unknown package", "not found", "permission denied"]:
            if marker in haystack:
                return False
        return True

    def _append_output_block(self, title, command, stdout, stderr, success, timestamp):
        result_text = "SUCCESS" if success else "FAILED"
        sections = [
            f"[{timestamp}] {title}",
            f"Command: {command}",
            f"Result: {result_text}",
        ]
        if stdout:
            sections.extend(["", "stdout:", stdout])
        if stderr:
            sections.extend(["", "stderr:", stderr])
        if not stdout and not stderr:
            sections.extend(["", "(no output)"])
        sections.append("\n" + "-" * 72)
        self.output_text.append("\n".join(sections))
        self.output_text.moveCursor(QTextCursor.End)

    def _append_output_message(self, title, message):
        self._append_output_block(title, "UI event", message, "", True, self._timestamp_now())

    def output_text_clear(self):
        self.output_text.clear()
        self._append_output_message("Output Cleared", "Command output panel was cleared.")

    def _timestamp_now(self):
        return datetime.now().strftime("%H:%M:%S")
