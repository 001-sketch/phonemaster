# PhoneMaster Toolkit

A professional-grade mobile device management toolkit — similar to Dr.Fone — built with Python + PySide6.

## Features

- 📱 **Device Detection** — Auto-detect connected Android & iOS devices
- ℹ️ **Device Info** — View model, OS, storage, battery, IMEI
- 📂 **File Manager** — Browse, upload, download, delete files
- 💾 **Backup & Restore** — Full/selective backup with one-click restore
- 🔄 **Phone Transfer** — Move data between Android and iOS devices

## Requirements

- Python 3.10+
- ADB (Android Debug Bridge) installed and on PATH
- iTunes or Apple Mobile Device drivers (for iOS support)

## Installation

```bash
cd phonemaster
pip install -r requirements.txt
```

## Usage

From the repository root, use the Windows launcher:

```bat
cd phonemaster
run.bat
```

Or run the module directly from the source directory:

```bash
cd src
python -m phonemaster
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| UI Framework | PySide6 (Qt 6) |
| Android | adbutils (ADB) |
| iOS | pymobiledevice3 |
| Icons | qtawesome (FontAwesome) |
| Theme | Custom QSS + dark/light |
