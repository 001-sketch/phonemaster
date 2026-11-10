"""Application configuration and constants."""

import os
from pathlib import Path

# App metadata
APP_NAME = "PhoneMaster"
APP_VERSION = "1.0.0"
APP_AUTHOR = "PhoneMaster Team"

# Paths
APP_DIR = Path(__file__).parent
RESOURCES_DIR = APP_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
STYLES_DIR = RESOURCES_DIR / "styles"

# User data
USER_DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "PhoneMaster"
BACKUP_DIR = USER_DATA_DIR / "backups"
LOG_DIR = USER_DATA_DIR / "logs"
SETTINGS_FILE = USER_DATA_DIR / "settings.json"

# Ensure user dirs exist
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Device polling interval (ms)
DEVICE_POLL_INTERVAL = 3000

# Supported file types for transfer
MEDIA_EXTENSIONS = {
    "images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"},
    "videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".3gp"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "documents": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"},
}

# Android paths
ANDROID_SDCARD = "/sdcard"
ANDROID_DCIM = "/sdcard/DCIM"
ANDROID_DOWNLOADS = "/sdcard/Download"
ANDROID_MUSIC = "/sdcard/Music"
ANDROID_DOCUMENTS = "/sdcard/Documents"

# Backup format version
BACKUP_FORMAT_VERSION = 1
