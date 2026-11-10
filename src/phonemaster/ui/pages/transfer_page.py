"""Phone Transfer page — direct data transfer between two connected mobile devices."""

from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QProgressBar, QMessageBox, QFrame
)
import qtawesome as qta

from phonemaster.models.device import DeviceInfo
from phonemaster.core.workers import Worker


class TransferPage(QWidget):
    """Device-to-device data migration page."""

    def __init__(self, device_manager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._devices: list[DeviceInfo] = []
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Phone to Phone Transfer")
        header.setObjectName("page_header")
        header.setStyleSheet("padding: 0px; font-size: 24px;")
        main_layout.addWidget(header)

        subtitle = QLabel("Seamlessly transfer photos, videos, music, and docs between Android and iOS")
        subtitle.setObjectName("page_subtitle")
        subtitle.setStyleSheet("padding: 0px 0px 15px 0px;")
        main_layout.addWidget(subtitle)

        # Transfer Cards Row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(20)

        # Source Card
        self.source_card = self._create_device_selector_card("Source Device (Copy From)", "fa5s.sign-out-alt", "#4fc3f7")
        self.combo_source = QComboBox()
        self.source_card._layout.addWidget(self.combo_source)
        self.lbl_source_info = QLabel("Select source device")
        self.lbl_source_info.setStyleSheet("color: #888; font-size: 12px;")
        self.source_card._layout.addWidget(self.lbl_source_info)
        cards_row.addWidget(self.source_card)

        # Transfer Center Arrow
        center_box = QVBoxLayout()
        center_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_icon = QLabel()
        arrow_icon.setPixmap(qta.icon("fa5s.arrow-circle-right", color="#e94560").pixmap(48, 48))
        arrow_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_box.addWidget(arrow_icon)
        cards_row.addLayout(center_box)

        # Destination Card
        self.dest_card = self._create_device_selector_card("Destination Device (Send To)", "fa5s.sign-in-alt", "#81c784")
        self.combo_dest = QComboBox()
        self.dest_card._layout.addWidget(self.combo_dest)
        self.lbl_dest_info = QLabel("Select target device")
        self.lbl_dest_info.setStyleSheet("color: #888; font-size: 12px;")
        self.dest_card._layout.addWidget(self.lbl_dest_info)
        cards_row.addWidget(self.dest_card)

        main_layout.addLayout(cards_row)

        # Transfer Options Card
        options_card = QFrame()
        options_card.setObjectName("device_card")
        options_card.setStyleSheet("""
            QFrame#device_card {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        options_layout = QVBoxLayout(options_card)
        options_layout.setSpacing(10)

        lbl_select = QLabel("Select Items to Transfer:")
        lbl_select.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        options_layout.addWidget(lbl_select)

        chk_layout = QHBoxLayout()
        self.cb_photos = QCheckBox("Photos")
        self.cb_photos.setChecked(True)
        self.cb_videos = QCheckBox("Videos")
        self.cb_videos.setChecked(True)
        self.cb_music = QCheckBox("Music")
        self.cb_music.setChecked(True)
        self.cb_docs = QCheckBox("Documents")
        self.cb_docs.setChecked(True)

        chk_layout.addWidget(self.cb_photos)
        chk_layout.addWidget(self.cb_videos)
        chk_layout.addWidget(self.cb_music)
        chk_layout.addWidget(self.cb_docs)
        chk_layout.addStretch()
        options_layout.addLayout(chk_layout)

        main_layout.addWidget(options_card)

        # Progress & Action
        main_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #888; font-size: 12px;")
        main_layout.addWidget(self.lbl_status)

        action_row = QHBoxLayout()
        action_row.addStretch()

        self.btn_start = QPushButton(" Start Phone Transfer")
        self.btn_start.setObjectName("primary_btn")
        self.btn_start.setIcon(qta.icon("fa5s.exchange-alt", color="#ffffff"))
        self.btn_start.clicked.connect(self._start_transfer)
        action_row.addWidget(self.btn_start)

        main_layout.addLayout(action_row)

    def _create_device_selector_card(self, title: str, icon: str, color: str) -> QFrame:
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
        layout.setSpacing(12)

        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon, color=color).pixmap(18, 18))
        header.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {color};")
        header.addWidget(title_lbl)
        header.addStretch()
        layout.addLayout(header)

        card._layout = layout
        return card

    def update_devices(self, devices: list[DeviceInfo]):
        self._devices = devices
        self.combo_source.clear()
        self.combo_dest.clear()

        for d in devices:
            text = f"{d.display_name} ({d.platform.value.upper()})"
            self.combo_source.addItem(text, d.serial)
            self.combo_dest.addItem(text, d.serial)

        if len(devices) >= 2:
            self.combo_dest.setCurrentIndex(1)

    def _start_transfer(self):
        src_idx = self.combo_source.currentIndex()
        dest_idx = self.combo_dest.currentIndex()

        if src_idx < 0 or dest_idx < 0 or src_idx == dest_idx:
            QMessageBox.warning(self, "Invalid Selection", "Please select two distinct devices for transfer.")
            return

        source_dev = self._devices[src_idx]
        dest_dev = self._devices[dest_idx]

        self.btn_start.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.lbl_status.setText(f"Migrating files from {source_dev.display_name} to {dest_dev.display_name}...")

        def run():
            temp_dir = tempfile.mkdtemp(prefix="pm_transfer_")
            # Pull files from source media folders
            paths_to_transfer = []
            files = self.device_manager.android.list_files(source_dev.serial, "/sdcard/DCIM")
            for f in files[:10]:  # batch of 10 items for demo/speed
                if not f.is_dir:
                    paths_to_transfer.append(f.path)

            return self.device_manager.transfer_files(
                source_dev.serial, source_dev.platform,
                dest_dev.serial, dest_dev.platform,
                paths_to_transfer, temp_dir
            )

        def on_done(result):
            self.btn_start.setEnabled(True)
            self.progress_bar.setVisible(False)
            success, fail = result
            self.lbl_status.setText(f"Transfer finished: {success} copied, {fail} failed.")
            QMessageBox.information(self, "Transfer Done", f"Transferred {success} files successfully.")

        worker = Worker(run)
        worker.signals.result.connect(on_done)
        QThreadPool.globalInstance().start(worker)
