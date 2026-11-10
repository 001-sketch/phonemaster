"""Unified device manager — combines Android and iOS services."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from phonemaster.config import BACKUP_DIR, BACKUP_FORMAT_VERSION
from phonemaster.models.device import (
    BackupInfo,
    DeviceInfo,
    DevicePlatform,
    FileItem,
)
from phonemaster.services.android_service import AndroidService
from phonemaster.services.ios_service import IOSService
from phonemaster.services.mtp_service import MtpService

logger = logging.getLogger("phonemaster.device_manager")


class DeviceManager:
    """
    Unified device manager that delegates to platform-specific services.
    This is the single entry point the UI layer uses for all operations.
    """

    def __init__(self):
        self.android = AndroidService()
        self.ios = IOSService()
        self.mtp = MtpService()
        self._current_device: Optional[DeviceInfo] = None
        self._devices: list[DeviceInfo] = []

    # ------------------------------------------------------------------ #
    #  Properties
    # ------------------------------------------------------------------ #

    @property
    def current_device(self) -> Optional[DeviceInfo]:
        return self._current_device

    @current_device.setter
    def current_device(self, device: Optional[DeviceInfo]):
        self._current_device = device

    @property
    def devices(self) -> list[DeviceInfo]:
        return self._devices

    # ------------------------------------------------------------------ #
    #  Device discovery
    # ------------------------------------------------------------------ #

    def scan_devices(self) -> list[DeviceInfo]:
        """Scan for all connected Android and iOS devices."""
        devices = []

        # 1. Scan Android via ADB (if debugging is enabled)
        try:
            android_devices = self.android.list_devices()
            devices.extend(android_devices)
        except Exception as e:
            logger.error("Android scan failed: %s", e)

        # 2. Scan iOS (via pymobiledevice3)
        try:
            ios_devices = self.ios.list_devices()
            devices.extend(ios_devices)
        except Exception as e:
            logger.error("iOS scan failed: %s", e)

        # 3. Scan Windows Portable Devices (MTP / Plug & Play) - just like Dr.Fone
        try:
            mtp_devices = self.mtp.list_devices()
            # Only add MTP devices that aren't already represented via ADB
            for m in mtp_devices:
                if not any(d.serial == m.serial for d in devices):
                    devices.append(m)
        except Exception as e:
            logger.error("MTP scan failed: %s", e)

        self._devices = devices
        return devices

    def get_device_info(self, serial: str, platform: DevicePlatform) -> DeviceInfo:
        """Get detailed info for a specific device."""
        if platform == DevicePlatform.ANDROID:
            return self.android.get_device_info(serial)
        elif platform == DevicePlatform.IOS:
            return self.ios.get_device_info(serial)
        else:
            return DeviceInfo(serial=serial)

    def select_device(self, serial: str) -> Optional[DeviceInfo]:
        """Select a device as the current working device and fetch full details."""
        for dev in self._devices:
            if dev.serial == serial:
                if "MTP" in dev.os_version:
                    self._current_device = dev
                else:
                    self._current_device = self.get_device_info(serial, dev.platform)
                return self._current_device
        return None

    # ------------------------------------------------------------------ #
    #  File operations (delegated)
    # ------------------------------------------------------------------ #

    def list_files(self, path: str = "") -> list[FileItem]:
        """List files on the current device."""
        if not self._current_device:
            return []
        dev = self._current_device
        if "MTP" in dev.os_version:
            return self.mtp.list_files(dev.name, path)
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.list_files(dev.serial, path or "/sdcard")
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.list_files(dev.serial, path or "/")
        return []

    def pull_file(self, remote_path: str, local_path: str) -> bool:
        if not self._current_device:
            return False
        dev = self._current_device
        if "MTP" in dev.os_version:
            return self.mtp.copy_from_device(dev.name, remote_path, local_path)
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.pull_file(dev.serial, remote_path, local_path)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.pull_file(dev.serial, remote_path, local_path)
        return False

    def push_file(self, local_path: str, remote_path: str) -> bool:
        if not self._current_device:
            return False
        dev = self._current_device
        if "MTP" in dev.os_version:
            return self.mtp.copy_to_device(dev.name, local_path, remote_path)
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.push_file(dev.serial, local_path, remote_path)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.push_file(dev.serial, local_path, remote_path)
        return False

    def delete_file(self, remote_path: str) -> bool:
        if not self._current_device:
            return False
        dev = self._current_device
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.delete_file(dev.serial, remote_path)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.delete_file(dev.serial, remote_path)
        return False

    def create_directory(self, remote_path: str) -> bool:
        if not self._current_device:
            return False
        dev = self._current_device
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.create_directory(dev.serial, remote_path)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.create_directory(dev.serial, remote_path)
        return False

    # ------------------------------------------------------------------ #
    #  Backup & Restore
    # ------------------------------------------------------------------ #

    def create_backup(self, categories: list[str] | None = None,
                      notes: str = "") -> Optional[BackupInfo]:
        """Create a backup of the current device."""
        if not self._current_device:
            return None

        dev = self._current_device
        backup_id = uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{dev.display_name}_{timestamp}"
        backup_path = BACKUP_DIR / backup_name

        logger.info("Starting backup: %s → %s", dev.display_name, backup_path)

        if dev.platform == DevicePlatform.ANDROID:
            success = self.android.backup_data(dev.serial, str(backup_path), categories=categories)
        elif dev.platform == DevicePlatform.IOS:
            success = self.ios.backup_data(dev.serial, str(backup_path))
        else:
            return None

        if not success:
            return None

        # Calculate backup size
        total_size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())

        backup_info = BackupInfo(
            backup_id=backup_id,
            device_name=dev.display_name,
            device_serial=dev.serial,
            platform=dev.platform,
            timestamp=timestamp,
            size_bytes=total_size,
            backup_path=str(backup_path),
            items=categories or ["full"],
            notes=notes,
        )

        # Save metadata
        meta_file = backup_path / "backup_meta.json"
        meta = {
            "version": BACKUP_FORMAT_VERSION,
            "backup_id": backup_info.backup_id,
            "device_name": backup_info.device_name,
            "device_serial": backup_info.device_serial,
            "platform": backup_info.platform.value,
            "timestamp": backup_info.timestamp,
            "size_bytes": backup_info.size_bytes,
            "items": backup_info.items,
            "notes": notes,
        }
        meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        logger.info("Backup completed: %s (%s)", backup_info.backup_id, backup_info.size_display)

        return backup_info

    def list_backups(self) -> list[BackupInfo]:
        """List all available backups."""
        backups = []
        if not BACKUP_DIR.exists():
            return backups

        for folder in BACKUP_DIR.iterdir():
            if not folder.is_dir():
                continue
            meta_file = folder / "backup_meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    backups.append(BackupInfo(
                        backup_id=meta["backup_id"],
                        device_name=meta["device_name"],
                        device_serial=meta["device_serial"],
                        platform=DevicePlatform(meta["platform"]),
                        timestamp=meta["timestamp"],
                        size_bytes=meta["size_bytes"],
                        backup_path=str(folder),
                        items=meta.get("items", []),
                        notes=meta.get("notes", ""),
                    ))
                except Exception as e:
                    logger.warning("Invalid backup metadata in %s: %s", folder, e)

        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    def restore_backup(self, backup_path: str,
                       categories: list[str] | None = None) -> bool:
        """Restore a backup to the current device."""
        if not self._current_device:
            return False

        dev = self._current_device
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.restore_data(dev.serial, backup_path, categories)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.restore_data(dev.serial, backup_path)
        return False

    # ------------------------------------------------------------------ #
    #  Screenshot
    # ------------------------------------------------------------------ #

    def take_screenshot(self, save_path: str) -> bool:
        if not self._current_device:
            return False
        dev = self._current_device
        if dev.platform == DevicePlatform.ANDROID:
            return self.android.take_screenshot(dev.serial, save_path)
        elif dev.platform == DevicePlatform.IOS:
            return self.ios.take_screenshot(dev.serial, save_path)
        return False

    # ------------------------------------------------------------------ #
    #  Transfer between devices
    # ------------------------------------------------------------------ #

    def transfer_files(self, source_serial: str, source_platform: DevicePlatform,
                       dest_serial: str, dest_platform: DevicePlatform,
                       remote_paths: list[str], temp_dir: str) -> tuple[int, int]:
        """
        Transfer files from one device to another via a local temp directory.
        Returns (success_count, fail_count).
        """
        temp = Path(temp_dir)
        temp.mkdir(parents=True, exist_ok=True)

        success = 0
        fail = 0

        for remote_path in remote_paths:
            filename = Path(remote_path).name
            local_temp = str(temp / filename)

            # Pull from source
            if source_platform == DevicePlatform.ANDROID:
                pulled = self.android.pull_file(source_serial, remote_path, local_temp)
            else:
                pulled = self.ios.pull_file(source_serial, remote_path, local_temp)

            if not pulled:
                fail += 1
                continue

            # Push to destination
            if dest_platform == DevicePlatform.ANDROID:
                dest_path = f"/sdcard/Transfer/{filename}"
                self.android.create_directory(dest_serial, "/sdcard/Transfer")
                pushed = self.android.push_file(dest_serial, local_temp, dest_path)
            else:
                dest_path = f"/Transfer/{filename}"
                self.ios.create_directory(dest_serial, "/Transfer")
                pushed = self.ios.push_file(dest_serial, local_temp, dest_path)

            if pushed:
                success += 1
            else:
                fail += 1

            # Clean up temp file
            try:
                Path(local_temp).unlink()
            except Exception:
                pass

        return success, fail
