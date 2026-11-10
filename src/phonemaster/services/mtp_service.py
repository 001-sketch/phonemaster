"""Windows Portable Devices (WPD / MTP) service.
Allows direct communication, file browsing, and transfer without USB debugging.
This is exactly how Dr.Fone detects phones out-of-the-box before developer mode is turned on.
"""

from __future__ import annotations

import logging
import os
import shutil
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

logger = logging.getLogger("phonemaster.mtp")


class MtpService:
    """Manages Windows Portable Device / MTP connections."""

    def __init__(self):
        self._shell = None

    def _get_shell(self):
        if self._shell is None:
            try:
                import win32com.client
                # 17 = ssfDRIVES (My Computer / This PC)
                self._shell = win32com.client.Dispatch("Shell.Application")
            except Exception as e:
                logger.error("Failed to initialize Windows Shell COM: %s", e)
        return self._shell

    def list_devices(self) -> list[DeviceInfo]:
        """Detect any portable devices (Android/Cameras/iOS MTP) plugged in via USB."""
        devices = []
        shell = self._get_shell()
        if not shell:
            return devices

        try:
            my_computer = shell.Namespace(17)
            if not my_computer:
                return devices

            for item in my_computer.Items():
                # Portable devices typically don't have standard DOS drive letters like C:\, D:\
                # and their path starts with "::{" or is a GUID virtual folder.
                item_path = str(item.Path)
                if not (item_path.startswith("::{") or item_path.startswith("\\\\?\\")):
                    continue

                name = item.Name
                # Verify that it has storage children (e.g. "Internal storage", "SD card")
                folder = item.GetFolder
                if not folder:
                    continue

                serial = item_path.split("\\")[-1] or name
                brand = "Samsung" if "samsung" in name.lower() or "a04" in name.lower() else "Android"
                
                info = DeviceInfo(
                    serial=name,  # User-friendly name as identifier in MTP mode
                    name=name,
                    brand=brand,
                    model=name,
                    platform=DevicePlatform.ANDROID,
                    connection=ConnectionType.USB,
                    os_version="MTP Mode (Plug & Play)"
                )

                # Try to calculate storage
                total_bytes = 0
                free_bytes = 0
                try:
                    for sub in folder.Items():
                        sub_folder = sub.GetFolder
                        if sub_folder:
                            # Parse space if available
                            pass
                except Exception:
                    pass

                devices.append(info)
        except Exception as e:
            logger.error("Error enumerating WPD / MTP devices: %s", e)

        return devices

    def _find_device_item(self, device_name: str):
        shell = self._get_shell()
        if not shell:
            return None
        my_comp = shell.Namespace(17)
        if not my_comp:
            return None
        clean_target = device_name.strip().lower()
        for item in my_comp.Items():
            name = item.Name.lower()
            if name == clean_target or clean_target in name or name in clean_target:
                return item
        return None

    def list_files(self, device_name: str, relative_path: str = "") -> list[FileItem]:
        """
        List files in an MTP folder.
        relative_path can be empty (""), or "Internal storage", "Internal storage/Pictures", etc.
        """
        items = []
        dev_item = self._find_device_item(device_name)
        if not dev_item:
            return items

        folder = dev_item.GetFolder
        if not folder:
            return items

        clean_path = relative_path.strip("/").replace("\\", "/")
        target_folder = folder

        if clean_path:
            parts = [p for p in clean_path.split("/") if p]
            curr = folder
            for part in parts:
                found = None
                for sub in curr.Items():
                    if sub.Name.lower() == part.lower():
                        found = sub.GetFolder
                        break
                if found:
                    curr = found
                else:
                    curr = None
                    break
            target_folder = curr

        if not target_folder:
            return items

        for sub in target_folder.Items():
            name = sub.Name
            is_folder = sub.IsFolder
            size = getattr(sub, "Size", 0) if not is_folder else 0
            rel = f"{clean_path}/{name}".strip("/")

            items.append(FileItem(
                name=name,
                path=rel,
                is_dir=is_folder,
                size=size,
                modified=""
            ))

        items.sort(key=lambda x: (not x.is_dir, x.name.lower()))
        return items

    def copy_from_device(self, device_name: str, remote_rel_path: str, local_dest_path: str) -> bool:
        """Download a file or folder from the MTP device to local PC."""
        shell = self._get_shell()
        if not shell:
            return False

        dev_item = self._find_device_item(device_name)
        if not dev_item:
            return False

        # Locate item
        parts = [p for p in remote_rel_path.strip("/").replace("\\", "/").split("/") if p]
        curr = dev_item.GetFolder
        target_item = None
        for i, part in enumerate(parts):
            for sub in curr.Items():
                if sub.Name.lower() == part.lower():
                    if i == len(parts) - 1:
                        target_item = sub
                    else:
                        curr = sub.GetFolder
                    break

        if not target_item:
            return False

        try:
            dest_dir = str(Path(local_dest_path).parent)
            Path(dest_dir).mkdir(parents=True, exist_ok=True)
            dest_folder = shell.Namespace(dest_dir)
            # CopyHere flag 16: Respond with 'Yes to All' for any dialog, 4: Do not display a progress dialog box
            dest_folder.CopyHere(target_item, 16)
            return True
        except Exception as e:
            logger.error("MTP copy from device failed: %s", e)
            return False

    def copy_to_device(self, device_name: str, local_src_path: str, remote_dest_folder_path: str) -> bool:
        """Upload a local file into an MTP folder."""
        shell = self._get_shell()
        if not shell:
            return False

        dev_item = self._find_device_item(device_name)
        if not dev_item:
            return False

        # Locate remote destination folder
        parts = [p for p in remote_dest_folder_path.strip("/").replace("\\", "/").split("/") if p]
        curr = dev_item.GetFolder
        for part in parts:
            found = None
            for sub in curr.Items():
                if sub.Name.lower() == part.lower():
                    found = sub.GetFolder
                    break
            if found:
                curr = found
            else:
                return False

        try:
            curr.CopyHere(str(Path(local_src_path).resolve()), 16)
            return True
        except Exception as e:
            logger.error("MTP copy to device failed: %s", e)
            return False
