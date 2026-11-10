"""Application bootstrap and entry point."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from phonemaster.core.logger import setup_logging
from phonemaster.ui.main_window import MainWindow


def main() -> int:
    """Initialize and run the PhoneMaster desktop application."""
    # Setup application logging
    logger = setup_logging()
    logger.info("Starting PhoneMaster Toolkit...")

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PhoneMaster")
    app.setOrganizationName("PhoneMaster")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
