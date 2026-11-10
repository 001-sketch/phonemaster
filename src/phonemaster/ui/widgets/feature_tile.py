"""Feature tile widget for the dashboard — clickable card with icon, title, description."""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor
import qtawesome as qta


class FeatureTile(QFrame):
    """Clickable feature tile for the dashboard grid."""

    clicked = Signal(int)  # Emits the page index to navigate to

    def __init__(self, icon_name: str, title: str, description: str,
                 page_index: int, color: str = "#e94560", parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.setObjectName("feature_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 160)
        self._setup_ui(icon_name, title, description, color)
        self._add_shadow()

    def _setup_ui(self, icon_name: str, title: str, description: str, color: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 15)
        layout.setSpacing(2)

        # Icon
        icon_label = QLabel()
        icon_label.setObjectName("feature_tile_icon")
        icon_label.setPixmap(qta.icon(icon_name, color=color).pixmap(40, 40))
        layout.addWidget(icon_label)

        layout.addStretch()

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("feature_tile_title")
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setObjectName("feature_tile_desc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index)
        super().mousePressEvent(event)
