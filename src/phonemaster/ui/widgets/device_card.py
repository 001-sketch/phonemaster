"""Device card widget — shows device info with selection support."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor
import qtawesome as qta

from phonemaster.models.device import DeviceInfo, DevicePlatform


class DeviceCard(QFrame):
    """Clickable device card showing device summary."""

    selected = Signal(str)  # Emits device serial when clicked

    def __init__(self, device: DeviceInfo, parent=None):
        super().__init__(parent)
        self.device = device
        self.setObjectName("device_card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(90)
        self.setMinimumWidth(280)
        self._setup_ui()
        self._add_shadow()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)

        # Platform icon
        icon_name = self.device.platform_icon
        color = "#3DDC84" if self.device.platform == DevicePlatform.ANDROID else "#ffffff"
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=color).pixmap(36, 36))
        icon_label.setFixedSize(42, 42)
        layout.addWidget(icon_label)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(self.device.display_name)
        name_label.setObjectName("device_name")
        info_layout.addWidget(name_label)

        os_label = QLabel(self.device.os_display)
        os_label.setObjectName("device_os")
        info_layout.addWidget(os_label)

        serial_label = QLabel(self.device.serial[:20] + "…" if len(self.device.serial) > 20 else self.device.serial)
        serial_label.setObjectName("device_serial")
        info_layout.addWidget(serial_label)

        layout.addLayout(info_layout, stretch=1)

        # Connection indicator
        conn_icon = "fa5s.usb" if self.device.connection.value == "usb" else "fa5s.wifi"
        conn_label = QLabel()
        conn_label.setPixmap(qta.icon(conn_icon, color="#00d25b").pixmap(16, 16))
        conn_label.setToolTip(f"Connected via {self.device.connection.value.upper()}")
        layout.addWidget(conn_label)

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def set_selected(self, is_selected: bool):
        self.setProperty("selected", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.device.serial)
        super().mousePressEvent(event)
