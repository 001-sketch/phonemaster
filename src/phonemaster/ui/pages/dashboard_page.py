"""Dashboard page — main landing page with feature tiles and device overview."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QScrollArea, QSpacerItem, QSizePolicy,
)
import qtawesome as qta

from phonemaster.ui.widgets.feature_tile import FeatureTile
from phonemaster.ui.widgets.device_card import DeviceCard
from phonemaster.ui.widgets.sidebar import Sidebar
from phonemaster.models.device import DeviceInfo


class DashboardPage(QWidget):
    """Main dashboard with feature tiles and connected device list."""

    navigate_to = Signal(int)  # Emits page index
    device_selected = Signal(str)  # Emits device serial

    def __init__(self, parent=None):
        super().__init__(parent)
        self._device_cards: list[DeviceCard] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(5)

        # --- Header ---
        header = QLabel("Welcome to PhoneMaster")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        main_layout.addWidget(header)

        subtitle = QLabel("Your all-in-one mobile device management toolkit")
        subtitle.setObjectName("page_subtitle")
        subtitle.setStyleSheet("padding: 0px 0px 15px 0px;")
        main_layout.addWidget(subtitle)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(25)

        # --- Connected Devices Section ---
        devices_header = QLabel("📱 Connected Devices")
        devices_header.setObjectName("section_title")
        scroll_layout.addWidget(devices_header)

        self.devices_container = QHBoxLayout()
        self.devices_container.setSpacing(15)
        self.devices_container.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Placeholder when no devices
        self.no_device_label = QLabel("  No devices connected. Connect a phone via USB to get started.")
        self.no_device_label.setObjectName("info_label")
        self.no_device_label.setStyleSheet("color: #666; padding: 20px; font-size: 13px;")

        devices_frame = QFrame()
        devices_inner = QVBoxLayout(devices_frame)
        devices_inner.setContentsMargins(0, 0, 0, 0)
        devices_inner.addLayout(self.devices_container)
        devices_inner.addWidget(self.no_device_label)
        scroll_layout.addWidget(devices_frame)

        # --- Feature Tiles Grid ---
        tools_header = QLabel("🛠️ Toolkit")
        tools_header.setObjectName("section_title")
        scroll_layout.addWidget(tools_header)

        tiles_grid = QGridLayout()
        tiles_grid.setSpacing(15)
        tiles_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)

        tiles = [
            ("fa5s.info-circle", "Device Info", "View hardware, OS,\nstorage & battery details",
             Sidebar.PAGE_DEVICE_INFO, "#4fc3f7"),
            ("fa5s.folder-open", "File Manager", "Browse, upload, download\n& manage device files",
             Sidebar.PAGE_FILE_MANAGER, "#81c784"),
            ("fa5s.database", "Backup & Restore", "Create full backups\n& restore anytime",
             Sidebar.PAGE_BACKUP, "#ffb74d"),
            ("fa5s.exchange-alt", "Phone Transfer", "Transfer data between\nAndroid & iOS devices",
             Sidebar.PAGE_TRANSFER, "#ce93d8"),
            ("fa5s.camera", "Screenshot", "Capture your device\nscreen instantly",
             Sidebar.PAGE_DEVICE_INFO, "#e57373"),
            ("fa5s.mobile-alt", "App Manager", "View & manage installed\napplications",
             Sidebar.PAGE_DEVICE_INFO, "#4db6ac"),
        ]

        for i, (icon, title, desc, page, color) in enumerate(tiles):
            tile = FeatureTile(icon, title, desc, page, color)
            tile.clicked.connect(self._on_tile_clicked)
            tiles_grid.addWidget(tile, i // 3, i % 3)

        scroll_layout.addLayout(tiles_grid)

        # --- Quick Stats ---
        stats_header = QLabel("📊 Quick Stats")
        stats_header.setObjectName("section_title")
        scroll_layout.addWidget(stats_header)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        self.stat_devices = self._create_stat_card("Connected", "0", "fa5s.plug", "#4fc3f7")
        self.stat_backups = self._create_stat_card("Backups", "0", "fa5s.database", "#ffb74d")
        self.stat_android = self._create_stat_card("Android", "—", "fa5b.android", "#3DDC84")
        self.stat_ios = self._create_stat_card("iOS", "—", "fa5b.apple", "#ffffff")

        stats_layout.addWidget(self.stat_devices)
        stats_layout.addWidget(self.stat_backups)
        stats_layout.addWidget(self.stat_android)
        stats_layout.addWidget(self.stat_ios)
        stats_layout.addStretch()

        scroll_layout.addLayout(stats_layout)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _create_stat_card(self, label: str, value: str, icon_name: str, color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
                min-width: 140px;
                max-width: 180px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(5)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(24, 24))
        layout.addWidget(icon_lbl)

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        value_lbl.setObjectName(f"stat_value_{label.lower()}")
        layout.addWidget(value_lbl)

        label_lbl = QLabel(label)
        label_lbl.setStyleSheet("font-size: 12px; color: #888;")
        layout.addWidget(label_lbl)

        # Store value label for updates
        card._value_label = value_lbl
        return card

    def _on_tile_clicked(self, page_index: int):
        self.navigate_to.emit(page_index)

    def update_devices(self, devices: list[DeviceInfo]):
        """Refresh the connected devices section."""
        # Clear existing cards
        for card in self._device_cards:
            card.deleteLater()
        self._device_cards.clear()

        self.no_device_label.setVisible(len(devices) == 0)

        for dev in devices:
            card = DeviceCard(dev)
            card.selected.connect(lambda serial: self.device_selected.emit(serial))
            self._device_cards.append(card)
            self.devices_container.addWidget(card)

        # Update stats
        self.stat_devices._value_label.setText(str(len(devices)))
        android_count = sum(1 for d in devices if d.platform.value == "android")
        ios_count = sum(1 for d in devices if d.platform.value == "ios")
        self.stat_android._value_label.setText(str(android_count) if android_count else "—")
        self.stat_ios._value_label.setText(str(ios_count) if ios_count else "—")

    def update_backup_count(self, count: int):
        self.stat_backups._value_label.setText(str(count))
