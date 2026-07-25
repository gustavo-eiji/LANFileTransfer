# LANFileTransfer (Work in Progress)

LANFileTransfer is a lightweight Python application that allows **direct file transfers between computers connected to the same local WiFi or Ethernet network**.

Unlike cloud storage or internet-based file sharing services, LANFileTransfer transfers files **directly through your local router (LAN)**. Files never leave your local network, resulting in faster transfers, improved privacy, and no internet bandwidth usage.

> **Current status:** Alpha (Work in Progress)

---

## Features

- Automatic device discovery using Zeroconf (Bonjour/mDNS)
- Cross-platform support
  - Windows
  - macOS (currently tested)
  - Linux (planned)
- Direct peer-to-peer transfers over the local network
- No account creation
- No cloud services
- No internet connection required after both devices are connected to the same network
- Progress bar during transfers
- Simple graphical interface (Tkinter)

---

## How it Works

1. Launch LANFileTransfer on two computers connected to the **same router/Wi-Fi network**.
2. Devices automatically discover each other using Zeroconf.
3. Select a device from the list.
4. Choose a file.
5. The file is transferred **directly over the local network**.

```
Computer A
      │
      │
      ▼
 Local Router (WiFi/Ethernet)
      ▲
      │
      │
Computer B
```

No data is uploaded to the internet.

---

## Requirements

Both computers must:

- Be connected to the **same local network**
- Have LANFileTransfer running
- Allow local network connections through the operating system firewall

Internet access is **not required** for transferring files.

---

## Current Status

The project is currently in Alpha.

Working features:

- Device discovery
- Windows ↔ Windows transfers
- Windows ↔ macOS transfers
- Direct LAN file transfers
- Large file support (currently under testing)
- Transfer progress bar

Known limitations:

- Minimal error handling
- No transfer cancellation
- Files are saved in the application's working directory
- No configurable destination folder yet
- Single transfer at a time

---

## Technologies Used

- Python 3.12+
- Tkinter
- Zeroconf
- TCP sockets
- PyInstaller

---

## Building

Clone the repository:

```bash
git clone https://github.com/gustavo-eiji/LANFileTransfer.git
cd LANFileTransfer
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run:

```bash
python main.py
```

---

## Packaging

### Windows

```bash
pyinstaller --windowed --onefile main.py
```

### macOS

```bash
pyinstaller --windowed --onefile main.py
```

---

## Roadmap

- Improved transfer reliability
- Better error reporting
- Transfer cancellation
- Destination folder selection
- Multiple simultaneous transfers
- Drag & Drop support
- Folder transfers
- Resume interrupted transfers
- Transfer speed indicator
- Estimated time remaining
- Settings window
- Automatic updates

---

## Why LANFileTransfer?

Most file-sharing applications rely on cloud storage or external servers.

MyShare was designed to keep file transfers:

- Local
- Fast
- Private
- Simple

Since files travel only through your local network infrastructure, transfer speed is limited primarily by your WiFi/Ethernet connection rather than your internet speed.

---

## License

This project is currently released for testing and educational purposes.

---

## Disclaimer

This software is under active development.

Expect bugs, incomplete features, and breaking changes between releases.

Feedback and bug reports are greatly appreciated.