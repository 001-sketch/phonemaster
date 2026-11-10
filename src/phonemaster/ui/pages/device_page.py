"""Device Info page — Displays comprehensive hardware, OS, battery, and storage details."""

import os
from pathlib import Path

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QScrollArea, QPushButton, QProgressBar, QFileDialog, QMessageBox
)
import qtawesome as qta

from phonemaster.models.device import DeviceInfo, DevicePlatform
from phonemaster.core.workers import Worker
from phonemaster.core.signals import app_signals


class DeviceInfoPage(QWidget):
    """Device Info page displaying detailed diagnostics and quick actions."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._current_device: DeviceInfo | None = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        header = QLabel("Device Diagnostics & Details")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        title_box.addWidget(header)

        subtitle = QLabel("Comprehensive hardware, OS, battery, and storage metrics")
        subtitle.setObjectName("page_subtitle")
        subtitle.setStyleSheet("padding: 0px 0px 5px 0px;")
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.btn_refresh = QPushButton(" Refresh")
        self.btn_refresh.setObjectName("toolbar_btn")
        self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#a8a8b3"))
        self.btn_refresh.clicked.connect(self._refresh_details)
        header_layout.addWidget(self.btn_refresh)

        self.btn_screenshot = QPushButton(" Take Screenshot")
        self.btn_screenshot.setObjectName("primary_btn")
        self.btn_screenshot.setIcon(qta.icon("fa5s.camera", color="#ffffff"))
        self.btn_screenshot.clicked.connect(self._take_screenshot)
        header_layout.addWidget(self.btn_screenshot)

        main_layout.addLayout(header_layout)

        # Content Area (Scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(20)

        # No device placeholder
        self.placeholder = QFrame()
        p_layout = QVBoxLayout(self.placeholder)
        p_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_icon = QLabel()
        p_icon.setPixmap(qta.icon("fa5s.mobile-alt", color="#333").pixmap(64, 64))
        p_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(p_icon)
        p_text = QLabel("No device selected")
        p_text.setStyleSheet("font-size: 16px; color: #666; font-weight: bold; padding-top: 10px;")
        p_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(p_text)
        p_hint = QLabel("Connect a smartphone via USB to view full specifications.")
        p_hint.setStyleSheet("font-size: 12px; color: #555;")
        p_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        p_layout.addWidget(p_hint)
        self.content_layout.addWidget(self.placeholder)

        # Device details view container
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setContentsMargins(0, 0, 0, 0)
        self.details_layout.setSpacing(20)

        # Grid of cards
        specs_grid = QGridLayout()
        specs_grid.setSpacing(15)

        # Basic Info Card
        self.card_basic = self._create_card("Device Information", "fa5s.info-circle", "#4fc3f7")
        self.lbl_model = QLabel("—")
        self.lbl_brand = QLabel("—")
        self.lbl_serial = QLabel("—")
        self.lbl_os = QLabel("—")
        self.lbl_connection = QLabel("—")
        self._add_row(self.card_basic._body_layout, "Model:", self.lbl_model)
        self._add_row(self.card_basic._body_layout, "Brand:", self.lbl_brand)
        self._add_row(self.card_basic._body_layout, "OS Version:", self.lbl_os)
        self._add_row(self.card_basic._body_layout, "Serial / UDID:", self.lbl_serial)
        self._add_row(self.card_basic._body_layout, "Connection:", self.lbl_connection)
        specs_grid.addWidget(self.card_basic, 0, 0)

        # Hardware & Network Card
        self.card_hw = self._create_card("Hardware & Network", "fa5s.microchip", "#ce93d8")
        self.lbl_imei = QLabel("—")
        self.lbl_resolution = QLabel("—")
        self.lbl_arch = QLabel("—")
        self.lbl_wifi = QLabel("—")
        self.lbl_root = QLabel("—")
        self._add_row(self.card_hw._body_layout, "IMEI:", self.lbl_imei)
        self._add_row(self.card_hw._body_layout, "Resolution:", self.lbl_resolution)
        self._add_row(self.card_hw._body_layout, "Architecture:", self.lbl_arch)
        self._add_row(self.card_hw._body_layout, "Wi-Fi MAC:", self.lbl_wifi)
        self._add_row(self.card_hw._body_layout, "Root / Jailbreak:", self.lbl_root)
        specs_grid.addWidget(self.card_hw, 0, 1)

        # Battery Card
        self.card_battery = self._create_card("Battery Status", "fa5s.battery-three-quarters", "#81c784")
        self.lbl_battery_level = QLabel("—%")
        self.lbl_battery_status = QLabel("—")
        self.lbl_battery_health = QLabel("—")
        self.lbl_battery_temp = QLabel("—")
        self.bar_battery = QProgressBar()
        self.bar_battery.setRange(0, 100)
        self.bar_battery.setValue(0)
        self.card_battery._body_layout.addWidget(self.bar_battery)
        self._add_row(self.card_battery._body_layout, "Charge Level:", self.lbl_battery_level)
        self._add_row(self.card_battery._body_layout, "Status:", self.lbl_battery_status)
        self._add_row(self.card_battery._body_layout, "Health:", self.lbl_battery_health)
        self._add_row(self.card_battery._body_layout, "Temperature:", self.lbl_battery_temp)
        specs_grid.addWidget(self.card_battery, 1, 0)

        # Storage Card
        self.card_storage = self._create_card("Internal Storage", "fa5s.hdd", "#ffb74d")
        self.lbl_storage_total = QLabel("— GB")
        self.lbl_storage_used = QLabel("— GB")
        self.lbl_storage_free = QLabel("— GB")
        self.bar_storage = QProgressBar()
        self.bar_storage.setRange(0, 100)
        self.bar_storage.setValue(0)
        self.card_storage._body_layout.addWidget(self.bar_storage)
        self._add_row(self.card_storage._body_layout, "Total Capacity:", self.lbl_storage_total)
        self._add_row(self.card_storage._body_layout, "Used Space:", self.lbl_storage_used)
        self._add_row(self.card_storage._body_layout, "Free Space:", self.lbl_storage_free)
        specs_grid.addWidget(self.card_storage, 1, 1)

        self.details_layout.addLayout(specs_grid)
        self.content_layout.addWidget(self.details_container)
        self.details_container.setVisible(False)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _create_card(self, title: str, icon: str, color: str) -> QFrame:
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
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color=color).pixmap(18, 18))
        header.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #0f3460; max-height: 1px;")
        layout.addWidget(sep)

        body_layout = QVBoxLayout()
        body_layout.setSpacing(6)
        layout.addLayout(body_layout)
        card._body_layout = body_layout
        return card

    def _add_row(self, layout: QVBoxLayout, label_text: str, value_label: QLabel):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #888; font-size: 12px;")
        value_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(value_label)
        layout.addLayout(row)

    def set_device(self, device: DeviceInfo | None):
        self._current_device = device
        if not device:
            self.placeholder.setVisible(True)
            self.details_container.setVisible(False)
            return

        self.placeholder.setVisible(False)
        self.details_container.setVisible(True)

        self.lbl_model.setText(device.model or "Unknown Model")
        self.lbl_brand.setText(device.brand or "Unknown Brand")
        self.lbl_os.setText(device.os_display)
        self.lbl_serial.setText(device.serial)
        self.lbl_connection.setText(device.connection.value.upper())

        self.lbl_imei.setText(device.imei or "N/A")
        self.lbl_resolution.setText(device.screen_resolution or "N/A")
        self.lbl_arch.setText(device.cpu_arch or "N/A")
        self.lbl_wifi.setText(device.wifi_mac or "N/A")
        root_txt = "Yes" if (device.is_rooted or device.is_jailbroken) else "No"
        self.lbl_root.setText(root_txt)

        # Battery
        bat = device.battery
        self.lbl_battery_level.setText(f"{bat.level}%")
        status_txt = "Charging" if bat.is_charging else "Discharging"
        self.lbl_battery_status.setText(status_txt)
        self.lbl_battery_health.setText(bat.health)
        temp_txt = f"{bat.temperature}°C" if bat.temperature > 0 else "N/A"
        self.lbl_battery_temp.setText(temp_txt)
        self.bar_battery.setValue(bat.level)

        # Storage
        st = device.storage
        if st.total_bytes > 0:
            self.lbl_storage_total.setText(f"{st.total_gb} GB")
            self.lbl_storage_used.setText(f"{st.used_gb} GB ({st.usage_percent}%)")
            self.lbl_storage_free.setText(f"{st.free_gb} GB")
            self.bar_storage.setValue(st.usage_percent)
        else:
            self.lbl_storage_total.setText("N/A")
            self.lbl_storage_used.setText("N/A")
            self.lbl_storage_free.setText("N/A")
            self.bar_storage.setValue(0)

    def _refresh_details(self):
        if not self._current_device:
            return
        serial = self._current_device.serial
        platform = self._current_device.platform

        def run_fetch():
            return self.device_manager.get_device_info(serial, platform)

        worker = Worker(run_fetch)
        worker.signals.result.connect(self.set_device)
        QThreadPool.globalInstance().start(worker)

    def _take_screenshot(self):
        if not self._current_device:
            QMessageBox.information(self, "No Device", "Please select a connected device first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", str(Path.home() / "screenshot.png"), "Images (*.png)"
        )
        if not file_path:
            return

        def run_capture():
            return self.device_manager.take_screenshot(file_path)

        def on_done(success):
            if success:
                QMessageBox.information(self, "Success", f"Screenshot saved successfully:\n{file_path}")
            else:
                QMessageBox.warning(self, "Error", "Failed to take screenshot.")

        worker = Worker(run_capture)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)
