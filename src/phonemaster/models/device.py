"""Device data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DevicePlatform(Enum):
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    USB = "usb"
    WIFI = "wifi"
    UNKNOWN = "unknown"


@dataclass
class StorageInfo:
    """Device storage information."""
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0

    @property
    def total_gb(self) -> float:
        return round(self.total_bytes / (1024 ** 3), 2)

    @property
    def used_gb(self) -> float:
        return round(self.used_bytes / (1024 ** 3), 2)

    @property
    def free_gb(self) -> float:
        return round(self.free_bytes / (1024 ** 3), 2)

    @property
    def usage_percent(self) -> int:
        if self.total_bytes == 0:
            return 0
        return int((self.used_bytes / self.total_bytes) * 100)


@dataclass
class BatteryInfo:
    """Device battery information."""
    level: int = 0               # 0-100
    is_charging: bool = False
    health: str = "Unknown"
    temperature: float = 0.0     # Celsius


@dataclass
class DeviceInfo:
    """Complete device information."""
    serial: str = ""
    name: str = "Unknown Device"
    brand: str = ""
    model: str = ""
    platform: DevicePlatform = DevicePlatform.UNKNOWN
    os_version: str = ""
    sdk_version: str = ""        # Android API level
    connection: ConnectionType = ConnectionType.UNKNOWN
    imei: str = ""
    phone_number: str = ""
    wifi_mac: str = ""
    storage: StorageInfo = field(default_factory=StorageInfo)
    battery: BatteryInfo = field(default_factory=BatteryInfo)
    is_rooted: bool = False      # Android
    is_jailbroken: bool = False  # iOS
    screen_resolution: str = ""
    cpu_arch: str = ""
    ram_mb: int = 0

    @property
    def display_name(self) -> str:
        if self.brand and self.model:
            return f"{self.brand} {self.model}"
        return self.name or self.serial or "Unknown Device"

    @property
    def os_display(self) -> str:
        prefix = "Android" if self.platform == DevicePlatform.ANDROID else "iOS"
        return f"{prefix} {self.os_version}" if self.os_version else prefix

    @property
    def platform_icon(self) -> str:
        """Return qtawesome icon name for the platform."""
        if self.platform == DevicePlatform.ANDROID:
            return "fa5b.android"
        elif self.platform == DevicePlatform.IOS:
            return "fa5b.apple"
        return "fa5s.mobile-alt"

    def to_dict(self) -> dict:
        return {
            "serial": self.serial,
            "name": self.name,
            "brand": self.brand,
            "model": self.model,
            "platform": self.platform.value,
            "os_version": self.os_version,
            "sdk_version": self.sdk_version,
            "connection": self.connection.value,
            "imei": self.imei,
            "storage_total": self.storage.total_bytes,
            "storage_used": self.storage.used_bytes,
            "battery_level": self.battery.level,
            "battery_charging": self.battery.is_charging,
            "screen_resolution": self.screen_resolution,
        }


@dataclass
class FileItem:
    """Represents a file/directory on a device."""
    name: str
    path: str
    is_dir: bool = False
    size: int = 0
    modified: str = ""
    permissions: str = ""

    @property
    def size_display(self) -> str:
        if self.is_dir:
            return "—"
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 ** 2:
            return f"{self.size / 1024:.1f} KB"
        elif self.size < 1024 ** 3:
            return f"{self.size / (1024**2):.1f} MB"
        else:
            return f"{self.size / (1024**3):.2f} GB"

    @property
    def extension(self) -> str:
        if self.is_dir:
            return ""
        parts = self.name.rsplit(".", 1)
        return f".{parts[1].lower()}" if len(parts) > 1 else ""

    @property
    def icon_name(self) -> str:
        """Return qtawesome icon name based on file type."""
        if self.is_dir:
            return "fa5s.folder"
        ext = self.extension
        if ext in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic"}:
            return "fa5s.image"
        elif ext in {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"}:
            return "fa5s.video"
        elif ext in {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}:
            return "fa5s.music"
        elif ext in {".pdf"}:
            return "fa5s.file-pdf"
        elif ext in {".doc", ".docx", ".txt", ".rtf"}:
            return "fa5s.file-word"
        elif ext in {".xls", ".xlsx", ".csv"}:
            return "fa5s.file-excel"
        elif ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
            return "fa5s.file-archive"
        elif ext in {".apk"}:
            return "fa5b.android"
        elif ext in {".ipa"}:
            return "fa5b.apple"
        return "fa5s.file"


@dataclass
class BackupInfo:
    """Represents a saved backup."""
    backup_id: str
    device_name: str
    device_serial: str
    platform: DevicePlatform
    timestamp: str
    size_bytes: int
    backup_path: str
    items: list = field(default_factory=list)  # List of backed up categories
    notes: str = ""

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024 ** 2:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 ** 3:
            return f"{self.size_bytes / (1024**2):.1f} MB"
        else:
            return f"{self.size_bytes / (1024**3):.2f} GB"
