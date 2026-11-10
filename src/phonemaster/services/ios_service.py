"""iOS device service — all iOS operations via pymobiledevice3."""

from __future__ import annotations

import asyncio
import inspect
import logging
import subprocess
import os
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

logger = logging.getLogger("phonemaster.ios")

# pymobiledevice3 imports — wrapped to handle missing dependency gracefully
_PMD3_AVAILABLE = False
try:
    from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient
    from pymobiledevice3.services.afc import AfcService
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    from pymobiledevice3.services.diagnostics import DiagnosticsService
    from pymobiledevice3.services.springboard import SpringBoardServicesService
    from pymobiledevice3.services.screenshot import ScreenshotService
    from pymobiledevice3.usbmux import list_devices as usbmux_list_devices
    _PMD3_AVAILABLE = True
except ImportError:
    logger.warning("pymobiledevice3 not installed — iOS features will be unavailable")


class IOSService:
    """Manages iOS device communication via pymobiledevice3."""

    def __init__(self):
        self._lockdown_clients: dict[str, object] = {}

    @property
    def is_available(self) -> bool:
        """Check if iOS support is available."""
        if not _PMD3_AVAILABLE:
            return False
        # Check if iTunes/Apple Mobile Device drivers are available
        try:
            self._get_usbmux_devices()
            return True  # usbmux is available even if no devices connected
        except Exception:
            return False

    def _get_usbmux_devices(self) -> list:
        """Helper to call usbmux_list_devices whether async or sync."""
        if not _PMD3_AVAILABLE:
            return []
        try:
            if inspect.iscoroutinefunction(usbmux_list_devices):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If running inside an existing loop
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            return executor.submit(asyncio.run, usbmux_list_devices()).result()
                    else:
                        return loop.run_until_complete(usbmux_list_devices())
                except RuntimeError:
                    return asyncio.run(usbmux_list_devices())
            else:
                res = usbmux_list_devices()
                if inspect.iscoroutine(res):
                    return asyncio.run(res)
                return res
        except Exception as e:
            logger.debug("usbmux check failed: %s", e)
            return []

    # ------------------------------------------------------------------ #
    #  Connection helpers
    # ------------------------------------------------------------------ #

    def _get_lockdown(self, udid: str | None = None) -> object:
        """Get or create a lockdown client for the device."""
        cache_key = udid or "__default__"
        if cache_key not in self._lockdown_clients:
            try:
                client = create_using_usbmux(serial=udid)
                self._lockdown_clients[cache_key] = client
            except Exception as e:
                logger.error("Failed to create lockdown client: %s", e)
                raise
        return self._lockdown_clients[cache_key]

    def _invalidate_lockdown(self, udid: str | None = None):
        """Remove cached lockdown client."""
        cache_key = udid or "__default__"
        self._lockdown_clients.pop(cache_key, None)

    # ------------------------------------------------------------------ #
    #  Device listing
    # ------------------------------------------------------------------ #

    def list_devices(self) -> list[DeviceInfo]:
        """List all connected iOS devices."""
        if not _PMD3_AVAILABLE:
            return []

        devices = []
        try:
            raw_devices = self._get_usbmux_devices()
            for device in raw_devices:
                udid = getattr(device, "serial", str(device))
                info = DeviceInfo(
                    serial=udid,
                    platform=DevicePlatform.IOS,
                    connection=ConnectionType.USB,
                )
                # Try to get basic info
                try:
                    lockdown = create_using_usbmux(serial=udid)
                    all_values = lockdown.all_values
                    info.name = all_values.get("DeviceName", "iPhone")
                    info.model = all_values.get("ProductType", "")
                    info.os_version = all_values.get("ProductVersion", "")
                    info.brand = "Apple"
                    info.cpu_arch = all_values.get("CPUArchitecture", "")
                    info.wifi_mac = all_values.get("WiFiAddress", "")
                    info.phone_number = all_values.get("PhoneNumber", "")
                    info.serial = all_values.get("UniqueDeviceID", udid)
                except Exception as e:
                    logger.debug("Could not get lockdown info for %s: %s", udid, e)

                devices.append(info)
        except Exception as e:
            logger.error("Failed to list iOS devices: %s", e)

        return devices

    def get_device_info(self, udid: str) -> DeviceInfo:
        """Get detailed information about a specific iOS device."""
        info = DeviceInfo(
            serial=udid,
            platform=DevicePlatform.IOS,
            brand="Apple",
            connection=ConnectionType.USB,
        )

        try:
            lockdown = self._get_lockdown(udid)
            values = lockdown.all_values

            info.name = values.get("DeviceName", "iPhone")
            info.model = values.get("ProductType", "")
            info.os_version = values.get("ProductVersion", "")
            info.cpu_arch = values.get("CPUArchitecture", "")
            info.wifi_mac = values.get("WiFiAddress", "")
            info.phone_number = values.get("PhoneNumber", "")
            info.imei = values.get("InternationalMobileEquipmentIdentity", "")
            info.screen_resolution = self._get_screen_resolution(values)

            # Storage
            try:
                disk = values.get("TotalDiskCapacity", 0)
                available = values.get("TotalDataAvailable", 0)
                info.storage = StorageInfo(
                    total_bytes=disk,
                    used_bytes=disk - available,
                    free_bytes=available,
                )
            except Exception:
                pass

            # Battery via diagnostics
            try:
                diag = DiagnosticsService(lockdown=lockdown)
                battery_info = diag.get_battery()
                info.battery = BatteryInfo(
                    level=int(battery_info.get("BatteryCurrentCapacity", 0)),
                    is_charging=battery_info.get("BatteryIsCharging", False),
                )
            except Exception:
                pass

        except Exception as e:
            logger.error("Error getting iOS device info for %s: %s", udid, e)

        return info

    def _get_screen_resolution(self, values: dict) -> str:
        """Derive screen resolution from device model."""
        model_resolutions = {
            "iPhone15,3": "2796x1290",  # iPhone 14 Pro Max
            "iPhone15,2": "2556x1179",  # iPhone 14 Pro
            "iPhone14,7": "2532x1170",  # iPhone 14
            "iPhone16,2": "2796x1290",  # iPhone 15 Pro Max
            "iPhone16,1": "2556x1179",  # iPhone 15 Pro
        }
        model = values.get("ProductType", "")
        return model_resolutions.get(model, "")

    # ------------------------------------------------------------------ #
    #  File management (via AFC)
    # ------------------------------------------------------------------ #

    def list_files(self, udid: str, path: str = "/") -> list[FileItem]:
        """List files in the device's media directory (sandboxed by Apple)."""
        if not _PMD3_AVAILABLE:
            return []

        items = []
        try:
            lockdown = self._get_lockdown(udid)
            afc = AfcService(lockdown=lockdown)
            entries = afc.listdir(path)

            for name in entries:
                if name in (".", ".."):
                    continue
                full_path = f"{path.rstrip('/')}/{name}"
                try:
                    stat = afc.stat(full_path)
                    is_dir = stat.get("st_ifmt") == "S_IFDIR"
                    size = int(stat.get("st_size", 0))
                    items.append(FileItem(
                        name=name,
                        path=full_path,
                        is_dir=is_dir,
                        size=size,
                    ))
                except Exception:
                    items.append(FileItem(name=name, path=full_path))

            items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        except Exception as e:
            logger.error("iOS file listing failed: %s", e)

        return items

    def pull_file(self, udid: str, remote_path: str, local_path: str) -> bool:
        """Download a file from the iOS device."""
        if not _PMD3_AVAILABLE:
            return False
        try:
            lockdown = self._get_lockdown(udid)
            afc = AfcService(lockdown=lockdown)
            data = afc.get_file_contents(remote_path)
            Path(local_path).write_bytes(data)
            return True
        except Exception as e:
            logger.error("iOS pull failed: %s", e)
            return False

    def push_file(self, udid: str, local_path: str, remote_path: str) -> bool:
        """Upload a file to the iOS device."""
        if not _PMD3_AVAILABLE:
            return False
        try:
            lockdown = self._get_lockdown(udid)
            afc = AfcService(lockdown=lockdown)
            data = Path(local_path).read_bytes()
            afc.set_file_contents(remote_path, data)
            return True
        except Exception as e:
            logger.error("iOS push failed: %s", e)
            return False

    def delete_file(self, udid: str, remote_path: str) -> bool:
        """Delete a file from the iOS device."""
        if not _PMD3_AVAILABLE:
            return False
        try:
            lockdown = self._get_lockdown(udid)
            afc = AfcService(lockdown=lockdown)
            afc.rm(remote_path)
            return True
        except Exception as e:
            logger.error("iOS delete failed: %s", e)
            return False

    def create_directory(self, udid: str, remote_path: str) -> bool:
        """Create a directory on the iOS device."""
        if not _PMD3_AVAILABLE:
            return False
        try:
            lockdown = self._get_lockdown(udid)
            afc = AfcService(lockdown=lockdown)
            afc.makedirs(remote_path)
            return True
        except Exception as e:
            logger.error("iOS mkdir failed: %s", e)
            return False

    # ------------------------------------------------------------------ #
    #  Backup & Restore
    # ------------------------------------------------------------------ #

    def backup_data(self, udid: str, backup_path: str) -> bool:
        """Create an iTunes-style backup of the iOS device using pymobiledevice3 CLI."""
        try:
            cmd = [
                "python", "-m", "pymobiledevice3", "backup2", "backup",
                "--full", backup_path, "--udid", udid,
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error("iOS backup failed: %s", e)
            return False

    def restore_data(self, udid: str, backup_path: str) -> bool:
        """Restore an iTunes-style backup to the iOS device."""
        try:
            cmd = [
                "python", "-m", "pymobiledevice3", "backup2", "restore",
                backup_path, "--udid", udid, "--system",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error("iOS restore failed: %s", e)
            return False

    # ------------------------------------------------------------------ #
    #  Screenshot
    # ------------------------------------------------------------------ #

    def take_screenshot(self, udid: str, save_path: str) -> bool:
        """Capture a screenshot from the iOS device."""
        if not _PMD3_AVAILABLE:
            return False
        try:
            lockdown = self._get_lockdown(udid)
            screenshot_svc = ScreenshotService(lockdown=lockdown)
            data = screenshot_svc.take_screenshot()
            Path(save_path).write_bytes(data)
            return True
        except Exception as e:
            logger.error("iOS screenshot failed: %s", e)
            return False

    # ------------------------------------------------------------------ #
    #  App management
    # ------------------------------------------------------------------ #

    def list_apps(self, udid: str) -> list[dict]:
        """List installed applications."""
        if not _PMD3_AVAILABLE:
            return []
        try:
            lockdown = self._get_lockdown(udid)
            proxy = InstallationProxyService(lockdown=lockdown)
            apps = proxy.get_apps("User")
            return [
                {
                    "bundle_id": bid,
                    "name": info.get("CFBundleDisplayName", bid),
                    "version": info.get("CFBundleShortVersionString", ""),
                }
                for bid, info in apps.items()
            ]
        except Exception as e:
            logger.error("iOS app listing failed: %s", e)
            return []
