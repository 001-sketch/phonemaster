"""Backup & Restore page — full & selective backup, history list, and restore operations."""

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QFrame, QSplitter
)
import qtawesome as qta

from phonemaster.models.device import DeviceInfo, BackupInfo
from phonemaster.core.workers import Worker


class BackupPage(QWidget):
    """Backup & Restore management page."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._current_device: DeviceInfo | None = None
        self._backups: list[BackupInfo] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Backup & Restore")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        main_layout.addWidget(header)

        subtitle = QLabel("Create safe local backups of your phone and restore whenever needed")
        subtitle.setObjectName("page_subtitle")
        subtitle.setStyleSheet("padding: 0px 0px 10px 0px;")
        main_layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Panel: Create Backup
        left_panel = QFrame()
        left_panel.setObjectName("device_card")
        left_panel.setStyleSheet("""
            QFrame#device_card {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(12)

        lbl_create = QLabel("📦 New Backup")
        lbl_create.setStyleSheet("font-size: 16px; font-weight: bold; color: #4fc3f7;")
        left_layout.addWidget(lbl_create)

        lbl_hint = QLabel("Select data categories to include in the backup:")
        lbl_hint.setStyleSheet("color: #888; font-size: 12px;")
        left_layout.addWidget(lbl_hint)

        self.cb_photos = QCheckBox("Photos & Gallery (DCIM)")
        self.cb_photos.setChecked(True)
        self.cb_videos = QCheckBox("Videos (Movies)")
        self.cb_videos.setChecked(True)
        self.cb_music = QCheckBox("Music & Audio")
        self.cb_music.setChecked(True)
        self.cb_documents = QCheckBox("Documents")
        self.cb_documents.setChecked(True)
        self.cb_downloads = QCheckBox("Downloads")
        self.cb_downloads.setChecked(True)

        left_layout.addWidget(self.cb_photos)
        left_layout.addWidget(self.cb_videos)
        left_layout.addWidget(self.cb_music)
        left_layout.addWidget(self.cb_documents)
        left_layout.addWidget(self.cb_downloads)

        left_layout.addStretch()

        self.progress_backup = QProgressBar()
        self.progress_backup.setVisible(False)
        left_layout.addWidget(self.progress_backup)

        self.lbl_backup_status = QLabel("")
        self.lbl_backup_status.setStyleSheet("color: #888; font-size: 11px;")
        left_layout.addWidget(self.lbl_backup_status)

        self.btn_start_backup = QPushButton(" Start Backup Now")
        self.btn_start_backup.setObjectName("primary_btn")
        self.btn_start_backup.setIcon(qta.icon("fa5s.save", color="#ffffff"))
        self.btn_start_backup.clicked.connect(self._start_backup)
        left_layout.addWidget(self.btn_start_backup)

        splitter.addWidget(left_panel)

        # Right Panel: Restore Existing Backups
        right_panel = QFrame()
        right_panel.setObjectName("device_card")
        right_panel.setStyleSheet("""
            QFrame#device_card {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)

        right_top = QHBoxLayout()
        lbl_history = QLabel("🗄️ Available Backups")
        lbl_history.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffb74d;")
        right_top.addWidget(lbl_history)
        right_top.addStretch()

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setObjectName("toolbar_btn")
        self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#a8a8b3"))
        self.btn_refresh.clicked.connect(self.reload_backups)
        right_top.addWidget(self.btn_refresh)
        right_layout.addLayout(right_top)

        self.table_backups = QTableWidget()
        self.table_backups.setColumnCount(4)
        self.table_backups.setHorizontalHeaderLabels(["Device", "Date", "Size", "Platform"])
        self.table_backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_backups.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_backups.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_backups.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_backups.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_backups.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        right_layout.addWidget(self.table_backups)

        right_bottom = QHBoxLayout()
        right_bottom.addStretch()

        self.btn_restore = QPushButton(" Restore to Connected Device")
        self.btn_restore.setObjectName("primary_btn")
        self.btn_restore.setIcon(qta.icon("fa5s.upload", color="#ffffff"))
        self.btn_restore.clicked.connect(self._restore_selected)
        right_bottom.addWidget(self.btn_restore)

        right_layout.addLayout(right_bottom)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 600])

        main_layout.addWidget(splitter)
        self.reload_backups()

    def set_device(self, device: DeviceInfo | None):
        self._current_device = device

    def reload_backups(self):
        self._backups = self.device_manager.list_backups()
        self.table_backups.setRowCount(len(self._backups))
        for row, b in enumerate(self._backups):
            self.table_backups.setItem(row, 0, QTableWidgetItem(b.device_name))
            self.table_backups.setItem(row, 1, QTableWidgetItem(b.timestamp))
            self.table_backups.setItem(row, 2, QTableWidgetItem(b.size_display))
            self.table_backups.setItem(row, 3, QTableWidgetItem(b.platform.value.upper()))

    def _start_backup(self):
        if not self._current_device:
            QMessageBox.information(self, "No Device", "Please select a connected device to backup.")
            return

        categories = []
        if self.cb_photos.isChecked(): categories.append("photos")
        if self.cb_videos.isChecked(): categories.append("videos")
        if self.cb_music.isChecked(): categories.append("music")
        if self.cb_documents.isChecked(): categories.append("documents")
        if self.cb_downloads.isChecked(): categories.append("downloads")

        if not categories:
            QMessageBox.warning(self, "No Selection", "Please select at least one data category.")
            return

        self.btn_start_backup.setEnabled(False)
        self.progress_backup.setVisible(True)
        self.progress_backup.setRange(0, 0)  # indeterminate
        self.lbl_backup_status.setText("Backing up selected categories...")

        def run_backup():
            return self.device_manager.create_backup(categories=categories)

        def on_done(result: BackupInfo | None):
            self.btn_start_backup.setEnabled(True)
            self.progress_backup.setVisible(False)
            if result:
                self.lbl_backup_status.setText(f"Backup created! ({result.size_display})")
                QMessageBox.information(self, "Backup Successful", f"Backup completed successfully!\nSize: {result.size_display}")
                self.reload_backups()
            else:
                self.lbl_backup_status.setText("Backup encountered an error.")
                QMessageBox.warning(self, "Backup Failed", "An error occurred during backup creation.")

        worker = Worker(run_backup)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)

    def _restore_selected(self):
        row = self.table_backups.currentRow()
        if row < 0 or row >= len(self._backups):
            QMessageBox.information(self, "Select Backup", "Please select a backup from the table to restore.")
            return

        if not self._current_device:
            QMessageBox.warning(self, "No Device", "Please connect and select a target device to restore into.")
            return

        backup = self._backups[row]
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore backup from '{backup.device_name}' into '{self._current_device.display_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        def run_restore():
            return self.device_manager.restore_backup(backup.backup_path)

        def on_done(success):
            if success:
                QMessageBox.information(self, "Restore Completed", "Data restore completed successfully!")
            else:
                QMessageBox.warning(self, "Restore Failed", "Encountered an issue during restore.")

        worker = Worker(run_restore)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)
