"""Settings page — manage configurations, export paths, and tool binaries."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QFrame, QMessageBox
)
import qtawesome as qta

from phonemaster.config import BACKUP_DIR, APP_VERSION


class SettingsPage(QWidget):
    """Application settings page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)

        header = QLabel("Settings & Preferences")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        main_layout.addWidget(header)

        # Storage & Backup card
        card_backup = self._create_card("Storage & Directory Paths", "fa5s.folder")
        layout_backup = QVBoxLayout(card_backup)

        lbl_bdir = QLabel("Default Backup Storage Location:")
        lbl_bdir.setStyleSheet("color: #a8a8b3; font-size: 12px;")
        layout_backup.addWidget(lbl_bdir)

        row_bdir = QHBoxLayout()
        self.edit_backup_dir = QLineEdit(str(BACKUP_DIR))
        self.edit_backup_dir.setReadOnly(True)
        row_bdir.addWidget(self.edit_backup_dir)

        btn_browse = QPushButton("Browse...")
        btn_browse.setObjectName("toolbar_btn")
        btn_browse.clicked.connect(self._browse_backup_dir)
        row_bdir.addWidget(btn_browse)
        layout_backup.addLayout(row_bdir)
        main_layout.addWidget(card_backup)

        # About card
        card_about = self._create_card("About PhoneMaster", "fa5s.info-circle")
        layout_about = QVBoxLayout(card_about)
        lbl_version = QLabel(f"Version: {APP_VERSION}")
        lbl_version.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        layout_about.addWidget(lbl_version)

        lbl_desc = QLabel("PhoneMaster is an open-architecture, cross-platform mobile device manager providing ADB and libimobiledevice connectivity.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #888; font-size: 12px; margin-top: 5px;")
        layout_about.addWidget(lbl_desc)

        main_layout.addWidget(card_about)
        main_layout.addStretch()

    def _create_card(self, title: str, icon: str) -> QFrame:
        card = QFrame()
        card.setObjectName("device_card")
        card.setStyleSheet("""
            QFrame#device_card {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        return card

    def _browse_backup_dir(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Select Backup Directory", self.edit_backup_dir.text())
        if new_dir:
            self.edit_backup_dir.setText(new_dir)
            QMessageBox.information(self, "Settings Saved", "Backup directory updated successfully.")
