"""Main application window — houses sidebar, header, and stacked pages."""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QFrame
)

from phonemaster.config import APP_NAME, APP_VERSION, STYLES_DIR, DEVICE_POLL_INTERVAL
from phonemaster.services.device_manager import DeviceManager
from phonemaster.models.device import DeviceInfo
from phonemaster.core.workers import DevicePollingThread

from phonemaster.ui.widgets.sidebar import Sidebar
from phonemaster.ui.pages.dashboard_page import DashboardPage
from phonemaster.ui.pages.device_page import DeviceInfoPage
from phonemaster.ui.pages.file_manager_page import FileManagerPage
from phonemaster.ui.pages.backup_page import BackupPage
from phonemaster.ui.pages.transfer_page import TransferPage
from phonemaster.ui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.device_manager = DeviceManager()
        self._setup_window()
        self._load_styles()
        self._setup_ui()
        self._start_device_polling()

    def _setup_window(self):
        self.setWindowTitle(f"{APP_NAME} - Mobile Device Toolkit v{APP_VERSION}")
        self.resize(1180, 760)
        self.setMinimumSize(950, 620)

    def _load_styles(self):
        qss_file = STYLES_DIR / "main.qss"
        if qss_file.exists():
            self.setStyleSheet(qss_file.read_text(encoding="utf-8"))

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        root_layout.addWidget(self.sidebar)

        # Right Content Container
        content_container = QWidget()
        content_container.setObjectName("content_area")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Stacked Pages
        self.stack = QStackedWidget()

        self.page_dashboard = DashboardPage()
        self.page_dashboard.navigate_to.connect(self._navigate_from_tile)
        self.page_dashboard.device_selected.connect(self._on_device_selected)

        self.page_device_info = DeviceInfoPage(self.device_manager)
        self.page_file_manager = FileManagerPage(self.device_manager)
        self.page_backup = BackupPage(self.device_manager)
        self.page_transfer = TransferPage(self.device_manager)
        self.page_settings = SettingsPage()

        self.stack.addWidget(self.page_dashboard)      # Index 0
        self.stack.addWidget(self.page_device_info)     # Index 1
        self.stack.addWidget(self.page_file_manager)    # Index 2
        self.stack.addWidget(self.page_backup)          # Index 3
        self.stack.addWidget(self.page_transfer)        # Index 4
        self.stack.addWidget(self.page_settings)        # Index 5

        content_layout.addWidget(self.stack)

        # Bottom Global Status Bar
        self.status_bar = QFrame()
        self.status_bar.setObjectName("status_bar")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(15, 6, 15, 6)

        self.lbl_status_device = QLabel("Ready")
        status_layout.addWidget(self.lbl_status_device)
        status_layout.addStretch()

        lbl_engine = QLabel("ADB & libimobiledevice Engine: Active")
        lbl_engine.setStyleSheet("color: #666; font-size: 11px;")
        status_layout.addWidget(lbl_engine)

        content_layout.addWidget(self.status_bar)
        root_layout.addWidget(content_container, stretch=1)

    def _switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active_page(index)

    def _navigate_from_tile(self, page_index: int):
        self._switch_page(page_index)

    def _on_device_selected(self, serial: str):
        dev = self.device_manager.select_device(serial)
        if dev:
            self.page_device_info.set_device(dev)
            self.page_file_manager.set_device(dev)
            self.page_backup.set_device(dev)
            self._switch_page(Sidebar.PAGE_DEVICE_INFO)

    def _start_device_polling(self):
        self.poll_thread = DevicePollingThread(
            poll_fn=self.device_manager.scan_devices,
            interval_ms=DEVICE_POLL_INTERVAL
        )
        self.poll_thread.devices_updated.connect(self._on_devices_updated)
        self.poll_thread.start()

    def _on_devices_updated(self, devices: list[DeviceInfo]):
        self.page_dashboard.update_devices(devices)
        self.page_transfer.update_devices(devices)
        backups = self.device_manager.list_backups()
        self.page_dashboard.update_backup_count(len(backups))

        if devices:
            first = devices[0]
            self.sidebar.update_device_status(True, first.display_name)
            self.lbl_status_device.setText(f"{len(devices)} device(s) connected.")
            if not self.device_manager.current_device:
                self.device_manager.select_device(first.serial)
                self.page_device_info.set_device(first)
                self.page_file_manager.set_device(first)
                self.page_backup.set_device(first)
        else:
            self.sidebar.update_device_status(False)
            self.lbl_status_device.setText("No mobile device detected.")
            self.device_manager.current_device = None

    def closeEvent(self, event):
        if hasattr(self, 'poll_thread') and self.poll_thread.isRunning():
            self.poll_thread.stop()
        super().closeEvent(event)
