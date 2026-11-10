"""Android device service — all ADB operations."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from phonemaster.models.device import (
    BatteryInfo,
    ConnectionType,
    DeviceInfo,
    DevicePlatform,
    FileItem,
    StorageInfo,
)

logger = logging.getLogger("phonemaster.android")


class AndroidService:
    """Manages Android device communication via ADB."""

    def __init__(self):
        self._adb_path = self._find_adb()
        self._connected_devices: dict[str, DeviceInfo] = {}

    # ------------------------------------------------------------------ #
    #  ADB discovery
    # ------------------------------------------------------------------ #

    def _find_adb(self) -> str:
        """Locate the adb executable."""
        # Check PATH first
        adb = shutil.which("adb")
        if adb:
            return adb

        # Check bundled adbutils binary
        try:
            import adbutils
            adb_bin = adbutils.adb_path()
            if adb_bin and Path(adb_bin).exists():
                return adb_bin
        except Exception:
            pass

        # Common install locations on Windows
        candidates = [
            Path(os.getenv("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path(os.getenv("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
            Path(os.getenv("ANDROID_SDK_ROOT", "")) / "platform-tools" / "adb.exe",
            Path("C:/Android/sdk/platform-tools/adb.exe"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)

        logger.warning("ADB not found — Android features will be unavailable")
        return "adb"  # Hope it's on PATH at runtime

    @property
    def is_available(self) -> bool:
        """Check if ADB is available and the server is running."""
        try:
            result = self._run_adb(["version"])
            return "Android Debug Bridge" in result
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  ADB execution helpers
    # ------------------------------------------------------------------ #

    def _run_adb(self, args: list[str], serial: str | None = None, timeout: int = 30) -> str:
        """Run an ADB command and return stdout."""
        cmd = [self._adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        logger.debug("ADB: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode != 0 and result.stderr.strip():
                logger.debug("ADB return code %s: %s", result.returncode, result.stderr.strip())
            return result.stdout.strip()
        except FileNotFoundError:
            logger.debug("ADB binary not found when running: %s", " ".join(cmd))
            return ""
        except Exception as e:
            logger.debug("ADB execution failed: %s", e)
            return ""

    def _shell(self, serial: str, command: str, timeout: int = 30) -> str:
        """Run a shell command on the device."""
        return self._run_adb(["shell", command], serial=serial, timeout=timeout)

    def _getprop(self, serial: str, prop: str) -> str:
        """Get a system property from the device."""
        return self._shell(serial, f"getprop {prop}")

    # ------------------------------------------------------------------ #
    #  Device listing
    # ------------------------------------------------------------------ #

    def list_devices(self) -> list[DeviceInfo]:
        """List all connected Android devices."""
        try:
            output = self._run_adb(["devices", "-l"])
        except Exception as e:
            logger.error("Failed to list devices: %s", e)
            return []

        devices = []
        for line in output.splitlines()[1:]:  # Skip header
            line = line.strip()
            if not line or "offline" in line:
                continue

            parts = line.split()
            if len(parts) < 2 or parts[1] != "device":
                continue

            serial = parts[0]
            # Parse extra info from -l output
            extra = {}
            for part in parts[2:]:
                if ":" in part:
                    k, v = part.split(":", 1)
                    extra[k] = v

            info = DeviceInfo(
                serial=serial,
                platform=DevicePlatform.ANDROID,
                model=extra.get("model", ""),
                brand=extra.get("device", ""),
                connection=ConnectionType.WIFI if ":" in serial else ConnectionType.USB,
            )
            devices.append(info)

        return devices

    def get_device_info(self, serial: str) -> DeviceInfo:
        """Get detailed information about a specific device."""
        info = DeviceInfo(
            serial=serial,
            platform=DevicePlatform.ANDROID,
            connection=ConnectionType.WIFI if ":" in serial else ConnectionType.USB,
        )

        try:
            info.brand = self._getprop(serial, "ro.product.brand").capitalize()
            info.model = self._getprop(serial, "ro.product.model")
            info.name = self._getprop(serial, "ro.product.name")
            info.os_version = self._getprop(serial, "ro.build.version.release")
            info.sdk_version = self._getprop(serial, "ro.build.version.sdk")
            info.cpu_arch = self._getprop(serial, "ro.product.cpu.abi")
            info.screen_resolution = self._get_screen_resolution(serial)
            info.imei = self._get_imei(serial)
            info.storage = self._get_storage_info(serial)
            info.battery = self._get_battery_info(serial)
            info.is_rooted = self._check_root(serial)
            info.wifi_mac = self._getprop(serial, "ro.boot.wifimacaddr")
        except Exception as e:
            logger.error("Error getting device info for %s: %s", serial, e)

        return info

    # ------------------------------------------------------------------ #
    #  Device details
    # ------------------------------------------------------------------ #

    def _get_screen_resolution(self, serial: str) -> str:
        output = self._shell(serial, "wm size")
        match = re.search(r"(\d+x\d+)", output)
        return match.group(1) if match else ""

    def _get_imei(self, serial: str) -> str:
        try:
            output = self._shell(serial, "service call iphonesubinfo 1")
            # Parse IMEI from service call output
            digits = re.findall(r"'(\d+)'", output)
            return "".join(digits).strip() if digits else ""
        except Exception:
            return ""

    def _get_storage_info(self, serial: str) -> StorageInfo:
        output = self._shell(serial, "df /data")
        for line in output.splitlines():
            if "/data" in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        total = int(parts[1]) * 1024  # df outputs in KB
                        used = int(parts[2]) * 1024
                        free = int(parts[3]) * 1024
                        return StorageInfo(total_bytes=total, used_bytes=used, free_bytes=free)
                    except (ValueError, IndexError):
                        pass
        return StorageInfo()

    def _get_battery_info(self, serial: str) -> BatteryInfo:
        output = self._shell(serial, "dumpsys battery")
        info = BatteryInfo()
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                info.level = int(line.split(":")[1].strip())
            elif line.startswith("status:"):
                status = int(line.split(":")[1].strip())
                info.is_charging = status in (2, 5)  # CHARGING or FULL
            elif line.startswith("health:"):
                health_map = {1: "Unknown", 2: "Good", 3: "Overheat", 4: "Dead", 5: "Over voltage", 6: "Failure"}
                info.health = health_map.get(int(line.split(":")[1].strip()), "Unknown")
            elif line.startswith("temperature:"):
                info.temperature = int(line.split(":")[1].strip()) / 10.0
        return info

    def _check_root(self, serial: str) -> bool:
        try:
            output = self._shell(serial, "su -c id")
            return "uid=0" in output
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  File management
    # ------------------------------------------------------------------ #

    def list_files(self, serial: str, path: str = "/sdcard") -> list[FileItem]:
        """List files and directories at the given path on the device."""
        output = self._shell(serial, f"ls -la {path}")
        items = []

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("total") or line.startswith("ls:"):
                continue

            parts = line.split(None, 7)
            if len(parts) < 7:
                continue

            permissions = parts[0]
            is_dir = permissions.startswith("d")
            size = 0
            try:
                size = int(parts[4]) if not is_dir else 0
            except (ValueError, IndexError):
                pass

            name = parts[-1] if len(parts) >= 8 else parts[6]
            if name in (".", ".."):
                continue

            full_path = f"{path.rstrip('/')}/{name}"
            modified = f"{parts[5]} {parts[6]}" if len(parts) >= 8 else ""

            items.append(FileItem(
                name=name,
                path=full_path,
                is_dir=is_dir,
                size=size,
                modified=modified,
                permissions=permissions,
            ))

        # Sort: directories first, then by name
        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        return items

    def pull_file(self, serial: str, remote_path: str, local_path: str) -> bool:
        """Download a file from the device."""
        try:
            self._run_adb(["pull", remote_path, local_path], serial=serial, timeout=300)
            return Path(local_path).exists()
        except Exception as e:
            logger.error("Pull failed: %s", e)
            return False

    def push_file(self, serial: str, local_path: str, remote_path: str) -> bool:
        """Upload a file to the device."""
        try:
            output = self._run_adb(["push", local_path, remote_path], serial=serial, timeout=300)
            return "pushed" in output.lower() or "file pushed" in output.lower()
        except Exception as e:
            logger.error("Push failed: %s", e)
            return False

    def delete_file(self, serial: str, remote_path: str) -> bool:
        """Delete a file or directory from the device."""
        try:
            self._shell(serial, f"rm -rf {remote_path}")
            return True
        except Exception as e:
            logger.error("Delete failed: %s", e)
            return False

    def create_directory(self, serial: str, remote_path: str) -> bool:
        """Create a directory on the device."""
        try:
            self._shell(serial, f"mkdir -p {remote_path}")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    #  Backup & Restore
    # ------------------------------------------------------------------ #

    def backup_data(self, serial: str, backup_path: str, include_apks: bool = True,
                    categories: list[str] | None = None) -> bool:
        """Create a backup of the device data."""
        backup_dir = Path(backup_path)
        backup_dir.mkdir(parents=True, exist_ok=True)

        success = True
        default_cats = categories or ["photos", "videos", "music", "documents", "downloads"]

        source_map = {
            "photos": "/sdcard/DCIM",
            "videos": "/sdcard/Movies",
            "music": "/sdcard/Music",
            "documents": "/sdcard/Documents",
            "downloads": "/sdcard/Download",
        }

        for cat in default_cats:
            source = source_map.get(cat)
            if not source:
                continue
            dest = backup_dir / cat
            dest.mkdir(exist_ok=True)
            try:
                self._run_adb(["pull", source + "/", str(dest)], serial=serial, timeout=600)
                logger.info("Backed up %s → %s", source, dest)
            except Exception as e:
                logger.error("Backup of %s failed: %s", cat, e)
                success = False

        # Backup contacts (as vCard)
        try:
            contacts_output = self._shell(serial, "content query --uri content://com.android.contacts/contacts --projection display_name")
            contacts_file = backup_dir / "contacts.txt"
            contacts_file.write_text(contacts_output, encoding="utf-8")
        except Exception as e:
            logger.warning("Contacts backup failed: %s", e)

        # Backup installed apps list
        try:
            apps = self._shell(serial, "pm list packages -3")
            apps_file = backup_dir / "installed_apps.txt"
            apps_file.write_text(apps, encoding="utf-8")
        except Exception as e:
            logger.warning("Apps list backup failed: %s", e)

        return success

    def restore_data(self, serial: str, backup_path: str,
                     categories: list[str] | None = None) -> bool:
        """Restore data from a backup to the device."""
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            logger.error("Backup path does not exist: %s", backup_path)
            return False

        dest_map = {
            "photos": "/sdcard/DCIM",
            "videos": "/sdcard/Movies",
            "music": "/sdcard/Music",
            "documents": "/sdcard/Documents",
            "downloads": "/sdcard/Download",
        }

        cats = categories or [d.name for d in backup_dir.iterdir() if d.is_dir()]
        success = True

        for cat in cats:
            source = backup_dir / cat
            dest = dest_map.get(cat, f"/sdcard/{cat}")
            if source.is_dir():
                try:
                    self._run_adb(["push", str(source) + "/", dest], serial=serial, timeout=600)
                    logger.info("Restored %s → %s", source, dest)
                except Exception as e:
                    logger.error("Restore of %s failed: %s", cat, e)
                    success = False

        return success

    # ------------------------------------------------------------------ #
    #  Screen capture
    # ------------------------------------------------------------------ #

    def take_screenshot(self, serial: str, save_path: str) -> bool:
        """Capture a screenshot from the device."""
        try:
            remote = "/sdcard/screenshot_temp.png"
            self._shell(serial, f"screencap -p {remote}")
            self._run_adb(["pull", remote, save_path], serial=serial)
            self._shell(serial, f"rm {remote}")
            return Path(save_path).exists()
        except Exception as e:
            logger.error("Screenshot failed: %s", e)
            return False

    # ------------------------------------------------------------------ #
    #  App management
    # ------------------------------------------------------------------ #

    def list_apps(self, serial: str, third_party_only: bool = True) -> list[str]:
        """List installed packages."""
        flag = "-3" if third_party_only else ""
        output = self._shell(serial, f"pm list packages {flag}")
        return [line.replace("package:", "").strip() for line in output.splitlines() if line.strip()]

    def install_apk(self, serial: str, apk_path: str) -> bool:
        """Install an APK on the device."""
        try:
            output = self._run_adb(["install", "-r", apk_path], serial=serial, timeout=120)
            return "success" in output.lower()
        except Exception as e:
            logger.error("APK install failed: %s", e)
            return False

    def uninstall_app(self, serial: str, package: str) -> bool:
        """Uninstall an app from the device."""
        try:
            output = self._run_adb(["uninstall", package], serial=serial, timeout=60)
            return "success" in output.lower()
        except Exception:
            return False
