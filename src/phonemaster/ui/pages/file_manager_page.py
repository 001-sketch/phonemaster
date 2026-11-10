"""File Manager page — Browse, upload, download, and delete device files."""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QMenu
)
import qtawesome as qta

from phonemaster.models.device import DeviceInfo, DevicePlatform, FileItem
from phonemaster.core.workers import Worker


class FileManagerPage(QWidget):
    """File manager for connected mobile devices."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._current_device: DeviceInfo | None = None
        self._current_path = "/sdcard"
        self._items: list[FileItem] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Device File Manager")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        main_layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.btn_up = QPushButton(" Up")
        self.btn_up.setObjectName("toolbar_btn")
        self.btn_up.setIcon(qta.icon("fa5s.arrow-up", color="#a8a8b3"))
        self.btn_up.clicked.connect(self._go_up)
        toolbar.addWidget(self.btn_up)

        self.path_input = QLineEdit()
        self.path_input.setText(self._current_path)
        self.path_input.returnPressed.connect(self._navigate_path)
        toolbar.addWidget(self.path_input, stretch=1)

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setObjectName("toolbar_btn")
        self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#a8a8b3"))
        self.btn_refresh.clicked.connect(self._reload_files)
        toolbar.addWidget(self.btn_refresh)

        self.btn_upload = QPushButton(" Upload File")
        self.btn_upload.setObjectName("toolbar_btn")
        self.btn_upload.setIcon(qta.icon("fa5s.upload", color="#a8a8b3"))
        self.btn_upload.clicked.connect(self._upload_file)
        toolbar.addWidget(self.btn_upload)

        self.btn_download = QPushButton(" Download")
        self.btn_download.setObjectName("toolbar_btn")
        self.btn_download.setIcon(qta.icon("fa5s.download", color="#a8a8b3"))
        self.btn_download.clicked.connect(self._download_selected)
        toolbar.addWidget(self.btn_download)

        self.btn_delete = QPushButton(" Delete")
        self.btn_delete.setObjectName("toolbar_btn")
        self.btn_delete.setIcon(qta.icon("fa5s.trash-alt", color="#e94560"))
        self.btn_delete.clicked.connect(self._delete_selected)
        toolbar.addWidget(self.btn_delete)

        main_layout.addLayout(toolbar)

        # Quick Links / Bookmarks
        bookmarks = QHBoxLayout()
        bookmarks.setSpacing(8)
        lbl_bm = QLabel("Quick Access:")
        lbl_bm.setStyleSheet("color: #666; font-size: 11px;")
        bookmarks.addWidget(lbl_bm)

        for name, p in [("Photos (DCIM)", "/sdcard/DCIM"), ("Downloads", "/sdcard/Download"),
                        ("Music", "/sdcard/Music"), ("Documents", "/sdcard/Documents")]:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #4fc3f7;
                    border: none;
                    text-decoration: underline;
                    font-size: 11px;
                }
                QPushButton:hover { color: #ffffff; }
            """)
            btn.clicked.connect(lambda _, target=p: self._go_to_path(target))
            bookmarks.addWidget(btn)
        bookmarks.addStretch()
        main_layout.addLayout(bookmarks)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Size", "Modified", "Permissions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        main_layout.addWidget(self.table)

        # Status Bar / Count
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #888; font-size: 11px;")
        main_layout.addWidget(self.lbl_status)

    def set_device(self, device: DeviceInfo | None):
        self._current_device = device
        if device:
            if "MTP" in device.os_version:
                self._current_path = "Internal storage"
            elif device.platform == DevicePlatform.IOS:
                self._current_path = "/"
            else:
                self._current_path = "/sdcard"
            self.path_input.setText(self._current_path)
            self._reload_files()
        else:
            self.table.setRowCount(0)
            self.lbl_status.setText("No device connected")

    def _go_to_path(self, path: str):
        if self._current_device and "MTP" in self._current_device.os_version:
            # Map standard sdcard paths to MTP storage
            if path.startswith("/sdcard/"):
                path = path.replace("/sdcard/", "Internal storage/")
            elif path == "/sdcard":
                path = "Internal storage"
        self._current_path = path
        self.path_input.setText(path)
        self._reload_files()

    def _go_up(self):
        if self._current_path in ("/", "/sdcard", ""):
            return
        parent = str(Path(self._current_path).parent).replace("\\", "/")
        if not parent or parent == ".":
            parent = ""
        self._go_to_path(parent)

    def _navigate_path(self):
        self._go_to_path(self.path_input.text().strip())

    def _reload_files(self):
        if not self._current_device:
            return

        self.lbl_status.setText("Loading files...")
        path = self._current_path

        def fetch():
            return self.device_manager.list_files(path)

        def on_loaded(items: list[FileItem]):
            self._items = items
            self.table.setRowCount(len(items))
            for row, item in enumerate(items):
                # Name & Icon
                name_item = QTableWidgetItem(item.name)
                name_item.setIcon(qta.icon(item.icon_name, color="#4fc3f7" if item.is_dir else "#ffffff"))
                self.table.setItem(row, 0, name_item)

                # Size
                size_item = QTableWidgetItem(item.size_display)
                size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, 1, size_item)

                # Modified
                self.table.setItem(row, 2, QTableWidgetItem(item.modified))

                # Permissions
                self.table.setItem(row, 3, QTableWidgetItem(item.permissions))

            dir_count = sum(1 for i in items if i.is_dir)
            file_count = len(items) - dir_count
            self.lbl_status.setText(f"{dir_count} directories, {file_count} files")

        worker = Worker(fetch)
        worker.signals.result.connect(on_loaded)
        QThreadPool.globalInstance().start(worker)

    def _on_cell_double_clicked(self, row: int, col: int):
        if row < 0 or row >= len(self._items):
            return
        item = self._items[row]
        if item.is_dir:
            self._go_to_path(item.path)

    def _get_selected_item(self) -> FileItem | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def _upload_file(self):
        if not self._current_device:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if not file_path:
            return

        dest_name = Path(file_path).name
        dest_path = f"{self._current_path.rstrip('/')}/{dest_name}"
        self.lbl_status.setText(f"Uploading {dest_name}...")

        def run_push():
            return self.device_manager.push_file(file_path, dest_path)

        def on_done(success):
            if success:
                self.lbl_status.setText("Upload successful")
                self._reload_files()
            else:
                QMessageBox.warning(self, "Upload Failed", f"Could not upload {dest_name}")

        worker = Worker(run_push)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)

    def _download_selected(self):
        item = self._get_selected_item()
        if not item or item.is_dir:
            QMessageBox.information(self, "Select File", "Please select a file to download.")
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save File As", str(Path.home() / item.name))
        if not save_path:
            return

        self.lbl_status.setText(f"Downloading {item.name}...")

        def run_pull():
            return self.device_manager.pull_file(item.path, save_path)

        def on_done(success):
            if success:
                QMessageBox.information(self, "Downloaded", f"File saved to:\n{save_path}")
                self.lbl_status.setText("Download completed")
            else:
                QMessageBox.warning(self, "Error", "Download failed.")

        worker = Worker(run_pull)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)

    def _delete_selected(self):
        item = self._get_selected_item()
        if not item:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete:\n{item.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run_del():
            return self.device_manager.delete_file(item.path)

        def on_done(success):
            if success:
                self._reload_files()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete item.")

        worker = Worker(run_del)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)

    def _show_context_menu(self, pos):
        item = self._get_selected_item()
        if not item:
            return
        menu = QMenu(self)
        if not item.is_dir:
            act_dl = menu.addAction("Download")
            act_dl.triggered.connect(self._download_selected)
        act_del = menu.addAction("Delete")
        act_del.triggered.connect(self._delete_selected)
        menu.exec(self.table.viewport().mapToGlobal(pos))
