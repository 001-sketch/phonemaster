"""Sidebar navigation widget — Dr.Fone-style left nav panel."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy,
)
import qtawesome as qta

from phonemaster.config import APP_NAME, APP_VERSION


class SidebarButton(QPushButton):
    """Custom sidebar navigation button."""

    def __init__(self, icon_name: str, text: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(f"  {text}")
        self.setIcon(qta.icon(icon_name, color="#a8a8b3", color_active="#e94560"))
        self.setIconSize(self.iconSize().__class__(20, 20))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)


class Sidebar(QFrame):
    """Left sidebar navigation panel."""

    page_changed = Signal(int)  # Emits the page index when nav changes

    # Page indices
    PAGE_DASHBOARD = 0
    PAGE_DEVICE_INFO = 1
    PAGE_FILE_MANAGER = 2
    PAGE_BACKUP = 3
    PAGE_TRANSFER = 4
    PAGE_SETTINGS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._buttons: list[SidebarButton] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo / Brand
        logo = QLabel(f"📱 {APP_NAME}")
        logo.setObjectName("sidebar_logo")
        layout.addWidget(logo)

        version = QLabel(f"v{APP_VERSION}")
        version.setObjectName("sidebar_version")
        layout.addWidget(version)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #0f3460; max-height: 1px; margin: 5px 15px;")
        layout.addWidget(sep)

        # Navigation buttons
        nav_items = [
            ("fa5s.th-large", "Dashboard"),
            ("fa5s.info-circle", "Device Info"),
            ("fa5s.folder-open", "File Manager"),
            ("fa5s.database", "Backup & Restore"),
            ("fa5s.exchange-alt", "Phone Transfer"),
            ("fa5s.cog", "Settings"),
        ]

        for i, (icon, text) in enumerate(nav_items):
            btn = SidebarButton(icon, text)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)

        # Spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Bottom info
        bottom_sep = QFrame()
        bottom_sep.setFrameShape(QFrame.Shape.HLine)
        bottom_sep.setStyleSheet("background-color: #0f3460; max-height: 1px; margin: 5px 15px;")
        layout.addWidget(bottom_sep)

        # Device status indicator
        self.device_status = QLabel("  ⚫  No Device Connected")
        self.device_status.setObjectName("device_status_indicator")
        self.device_status.setProperty("connected", False)
        self.device_status.setStyleSheet("padding: 10px 15px; font-size: 11px; color: #666;")
        layout.addWidget(self.device_status)

        # Select first button by default
        self._buttons[0].setChecked(True)

    def _on_button_clicked(self, index: int):
        """Handle nav button click — exclusive selection."""
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    def set_active_page(self, index: int):
        """Programmatically set the active page."""
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)

    def update_device_status(self, connected: bool, device_name: str = ""):
        """Update the bottom device status indicator."""
        if connected:
            self.device_status.setText(f"  🟢  {device_name}")
            self.device_status.setProperty("connected", True)
            self.device_status.setStyleSheet("padding: 10px 15px; font-size: 11px; color: #00d25b;")
        else:
            self.device_status.setText("  🔴  No Device Connected")
            self.device_status.setProperty("connected", False)
            self.device_status.setStyleSheet("padding: 10px 15px; font-size: 11px; color: #e94560;")
