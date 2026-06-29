import os
import json

from core import paths

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication

from core.ui.base_ui import eD_UIBase
from core.ui.dialogs.message_dialog import MessageDialog

class ExporterWindow(QMainWindow, eD_UIBase):
    def __init__(self, app_ref=None, parent=None):
        super().__init__(parent)
        self._init_ui_base(app=app_ref, context=getattr(app_ref, "context", None))

        self.setWindowTitle("File Content Exporter")
        self.setMinimumSize(980, 680)

        self.root_path = None
        self._all_files = []
        self._file_checks = {}
        self._filter_text = ""

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_backup = None
        self._status_style_backup = ""
        self._status_timer.timeout.connect(self._restore_preview_info)

        self._build_ui()
        self._apply_ui_style()
        self._load_last_root()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        central.setLayout(layout)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(8)
        header.setLayout(header_layout)

        title_row = QHBoxLayout()
        title = QLabel("File Content Exporter")
        title.setObjectName("titleLabel")
        self.lbl_root = QLabel("No root folder selected")
        self.lbl_root.setObjectName("rootLabel")
        self.lbl_root.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_root.setTextInteractionFlags(Qt.TextSelectableByMouse)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.lbl_root, 1)
        header_layout.addLayout(title_row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_select = QPushButton("Select Root Folder")
        self.btn_select.clicked.connect(self.select_root)

        self.btn_scan = QPushButton("Scan Root")
        self.btn_scan.clicked.connect(self.scan_root)

        self.btn_export = QPushButton("Export")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_selected)

        action_row.addWidget(self.btn_select)
        action_row.addWidget(self.btn_scan)
        action_row.addStretch()
        action_row.addWidget(self.btn_export)
        header_layout.addLayout(action_row)

        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)
        left_panel.setLayout(left_layout)

        files_group = QGroupBox("Files under root")
        files_layout = QVBoxLayout()
        files_layout.setContentsMargins(10, 12, 10, 10)
        files_layout.setSpacing(8)
        files_group.setLayout(files_layout)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter files...")
        self.search_input.textChanged.connect(self.on_search_change)

        self.btn_check_visible = QPushButton("Check Visible")
        self.btn_check_visible.clicked.connect(self.check_visible_files)

        self.btn_uncheck_visible = QPushButton("Uncheck Visible")
        self.btn_uncheck_visible.clicked.connect(self.uncheck_visible_files)

        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.btn_check_visible)
        search_row.addWidget(self.btn_uncheck_visible)
        files_layout.addLayout(search_row)

        self.files_stats = QLabel("Files: 0   Checked: 0")
        self.files_stats.setObjectName("metaLabel")
        files_layout.addWidget(self.files_stats)

        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.SingleSelection)
        self.files_list.itemChanged.connect(self._on_item_changed)
        self.files_list.itemDoubleClicked.connect(self._on_file_double_clicked)
        files_layout.addWidget(self.files_list, 1)

        left_layout.addWidget(files_group, 1)

        export_group = QGroupBox("Export List")
        export_layout = QVBoxLayout()
        export_layout.setContentsMargins(10, 12, 10, 10)
        export_layout.setSpacing(8)
        export_group.setLayout(export_layout)

        export_top = QHBoxLayout()
        self.export_stats = QLabel("Entries: 0")
        self.export_stats.setObjectName("metaLabel")

        self.btn_add = QPushButton("Add Checked")
        self.btn_add.clicked.connect(self.add_selected)

        self.btn_remove = QPushButton("Remove Selected")
        self.btn_remove.clicked.connect(self.remove_selected)

        self.btn_clear_export = QPushButton("Clear")
        self.btn_clear_export.clicked.connect(self.clear_export_list)

        export_top.addWidget(self.export_stats)
        export_top.addStretch()
        export_top.addWidget(self.btn_add)
        export_top.addWidget(self.btn_remove)
        export_top.addWidget(self.btn_clear_export)
        export_layout.addLayout(export_top)

        self.export_list = QListWidget()
        self.export_list.setSelectionMode(QListWidget.MultiSelection)
        export_layout.addWidget(self.export_list, 1)

        left_layout.addWidget(export_group, 1)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)
        right_panel.setLayout(right_layout)

        preview_group = QGroupBox("Export Preview")
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 12, 10, 10)
        preview_layout.setSpacing(8)
        preview_group.setLayout(preview_layout)

        preview_controls = QHBoxLayout()
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.clicked.connect(self.preview_export)
        self.btn_copy = QPushButton("Copy")
        self.btn_copy.clicked.connect(self.copy_export)
        self.preview_info = QLabel("")
        self.preview_info.setObjectName("metaLabel")
        self.preview_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        preview_controls.addWidget(self.btn_preview)
        preview_controls.addWidget(self.btn_copy)
        preview_controls.addStretch()
        preview_controls.addWidget(self.preview_info)
        preview_layout.addLayout(preview_controls)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Preview will appear here...")
        preview_layout.addWidget(self.preview, 1)

        right_layout.addWidget(preview_group, 1)
        splitter.addWidget(right_panel)

        splitter.setSizes([420, 560])

    def _apply_ui_style(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background: #111318;
            }
            QWidget {
                color: #e8eaed;
                font-size: 13px;
            }
            QFrame#header {
                background: #191c22;
                border: 1px solid #2a2f3a;
                border-radius: 12px;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel#rootLabel {
                color: #aab2c0;
            }
            QLabel#metaLabel {
                color: #8f98a8;
                font-size: 12px;
            }
            QGroupBox {
                background: #191c22;
                border: 1px solid #2a2f3a;
                border-radius: 12px;
                margin-top: 10px;
                font-weight: 600;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 10px;
            }
            QLineEdit, QTextEdit, QListWidget {
                background: #101217;
                border: 1px solid #2a2f3a;
                border-radius: 9px;
                padding: 8px;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
            }
            QListWidget {
                outline: none;
            }
            QListWidget::item {
                padding: 6px;
                margin: 1px 0;
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background: #202633;
            }
            QListWidget::item:selected {
                background: #263244;
                color: #ffffff;
            }

            QCheckBox::indicator,
            QListWidget::indicator {
                width: 16px;
                height: 16px;
                border-radius: 5px;
                border: 1px solid #46516a;
                background: #151922;
            }
            QCheckBox::indicator:hover,
            QListWidget::indicator:hover {
                border-color: #60a5fa;
                background: #1d2635;
            }
            QCheckBox::indicator:checked,
            QListWidget::indicator:checked {
                border: 1px solid #3b82f6;
                background: #2563eb;
                image: none;
            }
            QCheckBox::indicator:checked:hover,
            QListWidget::indicator:checked:hover {
                border-color: #60a5fa;
                background: #1d4ed8;
            }
            QCheckBox::indicator:disabled,
            QListWidget::indicator:disabled {
                border-color: #2a2f3a;
                background: #111318;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #343b4d;
                border-radius: 5px;
                min-height: 28px;
            }
            QScrollBar::handle:vertical:hover {
                background: #46516a;
            }
            QScrollBar::handle:vertical:pressed {
                background: #5b6b89;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 2px 4px 2px 4px;
            }
            QScrollBar::handle:horizontal {
                background: #343b4d;
                border-radius: 5px;
                min-width: 28px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #46516a;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #5b6b89;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
            }

            QPushButton {
                background: #242936;
                border: 1px solid #343b4d;
                border-radius: 8px;
                padding: 8px 12px;
                color: #eef2ff;
            }
            QPushButton:hover {
                background: #2d3444;
                border-color: #46516a;
            }
            QPushButton:pressed {
                background: #1d2330;
            }
            QPushButton#primaryButton {
                background: #2563eb;
                border-color: #3b82f6;
                color: #ffffff;
                font-weight: 700;
            }
            QPushButton#primaryButton:hover {
                background: #1d4ed8;
            }
            QSplitter::handle {
                background: transparent;
            }
            """
        )

    def _load_last_root(self):
        try:
            cfg = self._load_cache_config() or {}
            saved = cfg.get("last_root", "")
            if saved and os.path.isdir(saved):
                self.root_path = saved
                self.lbl_root.setText(saved)
                self.scan_root()
        except Exception:
            pass

    def select_root(self):
        path = QFileDialog.getExistingDirectory(self, "Select Root Folder")
        if path:
            self.root_path = path
            self.lbl_root.setText(path)
            try:
                self._save_cache_config({"last_root": path})
            except Exception:
                pass
            self.scan_root()

    def scan_root(self):
        self._all_files = []
        self._file_checks = {}

        if not self.root_path or not os.path.isdir(self.root_path):
            MessageDialog.warning(self, "No root", "Please select a valid root folder first.")
            self._update_stats()
            return

        for dirpath, _, filenames in os.walk(self.root_path):
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, self.root_path)
                self._all_files.append(rel)
                self._file_checks[rel] = False

        self._all_files.sort(key=lambda value: value.lower())
        self.refresh_files_view()
        self._show_temp_status("Scan complete", color="#22c55e")

    def refresh_files_view(self):
        self.files_list.blockSignals(True)
        try:
            self.files_list.clear()
            ft = (self._filter_text or "").lower()

            for rel in self._all_files:
                if ft and ft not in rel.lower():
                    continue

                item = QListWidgetItem(rel)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setCheckState(Qt.Checked if self._file_checks.get(rel, False) else Qt.Unchecked)
                self.files_list.addItem(item)
        finally:
            self.files_list.blockSignals(False)

        self._update_stats()
        
    def _add_export_item(self, rel: str):
        existing = set(self.export_list.item(i).text() for i in range(self.export_list.count()))

        if rel in existing:
            self._show_temp_status("Already in export list", color="#f59e0b")
            return False

        self.export_list.addItem(rel)
        self._update_stats()
        self._show_temp_status("Added 1 file", color="#22c55e")
        return True

    def add_selected(self):
        items = [p for p in self._all_files if self._file_checks.get(p)]

        if not items:
            MessageDialog.info(self, "No selection", "No checked files to add.")
            return

        existing = set(self.export_list.item(i).text() for i in range(self.export_list.count()))

        added = 0
        for p in items:
            if p in existing:
                continue
            self.export_list.addItem(p)
            added += 1

        self._update_stats()

        if added:
            self._show_temp_status(f"Added {added} file(s)", color="#22c55e")
        else:
            self._show_temp_status("Already in export list", color="#f59e0b")

    def remove_selected(self):
        for it in self.export_list.selectedItems():
            row = self.export_list.row(it)
            self.export_list.takeItem(row)

        self._update_stats()

    def clear_export_list(self):
        if self.export_list.count() == 0:
            return

        self.export_list.clear()
        self._update_stats()
        self._show_temp_status("Export list cleared", color="#f59e0b")

    def export_selected(self):
        if self.export_list.count() == 0:
            MessageDialog.info(self, "No files", "Export list is empty.")
            return

        if not self.root_path:
            MessageDialog.warning(self, "No root", "Root folder is not set.")
            return

        fname, _ = QFileDialog.getSaveFileName(self, "Save Export", filter="Text files (*.txt);;All files (*)")
        if not fname:
            return

        try:
            text = self.build_export_text()
            with open(fname, "w", encoding="utf-8") as out:
                out.write(text)

            self.preview.setPlainText(text)
            self._update_preview_info(text)

            MessageDialog.info(self, "Exported", f"Exported {self.export_list.count()} entries to {fname}")
        except Exception as e:
            MessageDialog.error(self, "Error", f"Failed to write export: {e}")

    def on_search_change(self, text: str):
        self._filter_text = text or ""
        self.refresh_files_view()

    def check_visible_files(self):
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            self._file_checks[item.text()] = True

        self.refresh_files_view()

    def uncheck_visible_files(self):
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            self._file_checks[item.text()] = False

        self.refresh_files_view()

    def _on_item_changed(self, item: QListWidgetItem):
        rel = item.text()
        self._file_checks[rel] = item.checkState() == Qt.Checked
        self._update_stats()

    def _on_file_double_clicked(self, item: QListWidgetItem):
        rel = item.text()

        if rel not in self._all_files:
            return

        self._add_export_item(rel)

    def build_export_text(self) -> str:
        out_lines = []

        for i in range(self.export_list.count()):
            rel = self.export_list.item(i).text()
            full = os.path.join(self.root_path or "", rel)
            out_lines.append(f"{rel}:\n")

            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    out_lines.append(f.read())
            except Exception as e:
                out_lines.append(f"<error reading file: {e}>\n")

            out_lines.append("\n\n")

        return "".join(out_lines)

    def preview_export(self):
        if self.export_list.count() == 0:
            MessageDialog.info(self, "No files", "Export list is empty.")
            return

        text = self.build_export_text()
        self.preview.setPlainText(text)
        self._update_preview_info(text)

    def copy_export(self):
        text = self.preview.toPlainText()

        if not text:
            text = self.build_export_text()
            if not text:
                MessageDialog.info(self, "No content", "Nothing to copy.")
                return

            self.preview.setPlainText(text)
            self._update_preview_info(text)

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self._show_temp_status("Copied", color="#22c55e")

    def closeEvent(self, event):
        try:
            if self.root_path:
                self._save_cache_config({"last_root": self.root_path})
        except Exception:
            pass

        try:
            super().closeEvent(event)
        except Exception:
            event.accept()

    def showEvent(self, event):
        try:
            try:
                QTimer.singleShot(200, self._do_center)
            except Exception:
                screen = self.screen() or QGuiApplication.primaryScreen()
                if screen is not None:
                    center_point = screen.availableGeometry().center()
                    fg = self.frameGeometry()
                    fg.moveCenter(center_point)
                    self.move(fg.topLeft())
        except Exception:
            pass

        try:
            super().showEvent(event)
        except Exception:
            pass

    def _do_center(self):
        try:
            screen = self.screen() or QGuiApplication.primaryScreen()
            if screen is not None:
                center_point = screen.availableGeometry().center()
                fg = self.frameGeometry()
                fg.moveCenter(center_point)
                self.move(fg.topLeft())

                try:
                    if hasattr(self, "raise_"):
                        self.raise_()
                    if hasattr(self, "activateWindow"):
                        self.activateWindow()
                except Exception:
                    pass
        except Exception:
            pass

    def _do_center_and_mark(self):
        try:
            self._do_center()
        except Exception:
            pass

    def _cache_config_path(self):
        try:
            app_id = getattr(self.app, "id", None) or getattr(self.app, "manifest", {}).get("id", "")
            paths.ensure_app_cache_dir(app_id)
            return paths.get_app_cache_dir(app_id) / "config.json"
        except Exception:
            return None

    def _load_cache_config(self):
        p = self._cache_config_path()

        if not p:
            return {}

        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass

        return {}

    def _save_cache_config(self, updates: dict):
        p = self._cache_config_path()

        if not p:
            return False

        try:
            data = {}

            if p.exists():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            data.update(updates or {})
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception:
            return False

    def _update_stats(self):
        checked = sum(1 for value in self._file_checks.values() if value)
        visible = self.files_list.count() if hasattr(self, "files_list") else 0
        total = len(self._all_files)
        export_count = self.export_list.count() if hasattr(self, "export_list") else 0

        if hasattr(self, "files_stats"):
            self.files_stats.setText(f"Files: {total}   Visible: {visible}   Checked: {checked}")

        if hasattr(self, "export_stats"):
            self.export_stats.setText(f"Entries: {export_count}")

    def _update_preview_info(self, text: str):
        if text is None:
            self.preview_info.setText("")
            return

        lines = text.count("\n")

        if text and not text.endswith("\n"):
            lines = max(lines, len(text.splitlines()))

        chars = len(text)
        self.preview_info.setText(f"Lines: {lines}   Characters: {chars}")

    def _show_temp_status(self, msg: str, color: str = None, seconds: float = 2.0):
        try:
            was_active = self._status_timer.isActive()

            if was_active:
                self._status_timer.stop()

            # Keep the original preview info while replacing one temporary status
            # with another temporary status.
            if not was_active:
                try:
                    self._status_backup = self.preview_info.text()
                except Exception:
                    self._status_backup = ""

                try:
                    self._status_style_backup = self.preview_info.styleSheet()
                except Exception:
                    self._status_style_backup = ""

            try:
                if color:
                    self.preview_info.setStyleSheet(f"color: {color};")
                else:
                    self.preview_info.setStyleSheet(self._status_style_backup or "")
            except Exception:
                pass

            self.preview_info.setText(msg)
            self._status_timer.start(int(max(0.0, float(seconds)) * 1000))
        except Exception:
            pass


    def _restore_preview_info(self):
        try:
            if self._status_backup is None:
                self.preview_info.setText("")
            else:
                self.preview_info.setText(self._status_backup)

            try:
                self.preview_info.setStyleSheet(self._status_style_backup or "")
            except Exception:
                pass

            self._status_backup = None
            self._status_style_backup = ""
        except Exception:
            pass
