# LANFileTransfer (Work in Progress)

Lightweight, cross-platform LAN file transfers with automatic discovery and integrity verification. **direct file transfers between computers connected to the same local WiFi or Ethernet network**.

Unlike cloud storage or internet-based file sharing services, LANFileTransfer transfers files **directly through your local router (LAN)**. Files never leave your local network, resulting in faster transfers, improved privacy, and no internet bandwidth usage.

> **Current status:** Alpha (Work in Progress)

---

## Features

- Automatic device discovery using Zeroconf (Bonjour/mDNS)
- Cross-platform support
  - Windows
  - macOS
  - Linux (planned)
- Direct file transfers over the local network
- SHA-256 integrity verification after every transfer
- HMAC-based authentication using a shared security code
- Protocol version checking for compatibility
- Custom protocol identifier to reject non-LANFileTransfer traffic
- Automatic handling of duplicate filenames (`file (1).txt`)
- Progress bar during transfers
- Simple graphical interface (Tkinter)
- No account creation
- No cloud services
- No internet connection required after devices are connected to the same LAN

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

## Security

LANFileTransfer includes several safeguards to prevent accidental or unauthorized communication.

Current protections include:

- SHA-256 verification of every transferred file
- HMAC authentication using a shared security code
- Protocol identifier ("magic bytes") to reject unrelated TCP traffic
- Protocol version validation to prevent incompatible clients from communicating
- Socket timeouts to avoid indefinitely stalled connections

Future releases are planned to expand these protections further.

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

- Automatic device discovery
- Windows ↔ Windows transfers
- Windows ↔ macOS transfers
- Large file transfers
- Transfer progress bar
- SHA-256 file integrity verification
- Protocol compatibility validation
- HMAC authentication using a shared security code
- Automatic duplicate filename handling
- Socket timeout protection
- Custom password setting

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

- Better error reporting
- Transfer cancellation
- Destination folder selection
- Multiple simultaneous transfers
- Drag & Drop support
- Folder transfers
- Resume interrupted transfers
- Transfer speed indicator
- Estimated time remaining
- Automatic updates
- Linux support
- Mobile support
- End-to-end encryption

---

## Why LANFileTransfer?

Many file-sharing applications rely on cloud storage, third-party servers, or internet connectivity.

LANFileTransfer is designed to transfer files directly between computers on the same local network.

Benefits include:

- Faster transfers on modern LANs
- No cloud uploads
- No internet bandwidth usage
- Greater privacy
- Minimal setup
- Cross-platform compatibility

Transfer speed is limited primarily by your local network hardware (Wi-Fi or Ethernet) rather than your internet connection.
---

## License

This project is currently released for testing and educational purposes.

---

## Disclaimer

This software is under active development.

Expect bugs, incomplete features, and breaking changes between releases.

Feedback and bug reports are greatly appreciated.