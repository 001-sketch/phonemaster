"""Global application signals / event bus for thread-safe communication."""

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """Centralized signal bus for cross-component communication."""

    # Device signals
    device_connected = Signal(dict)       # Emitted when a new device is detected
    device_disconnected = Signal(str)     # Emitted with device serial when disconnected
    device_list_updated = Signal(list)    # Full device list refresh

    # Operation signals
    operation_started = Signal(str)       # Operation name
    operation_progress = Signal(str, int) # Operation name, percent (0-100)
    operation_completed = Signal(str, bool, str)  # name, success, message
    operation_log = Signal(str)           # Log line for status bar

    # File manager signals
    file_list_ready = Signal(list)        # List of file dicts
    file_transfer_progress = Signal(str, int, int)  # filename, transferred, total

    # Backup signals
    backup_progress = Signal(int, str)    # percent, current item
    backup_completed = Signal(bool, str)  # success, path or error message
    restore_progress = Signal(int, str)
    restore_completed = Signal(bool, str)

    # Transfer signals
    transfer_progress = Signal(int, int, str)  # current, total, item name
    transfer_completed = Signal(bool, str)

    # Error signals
    error_occurred = Signal(str, str)     # title, message


# Singleton instance
app_signals = AppSignals()
