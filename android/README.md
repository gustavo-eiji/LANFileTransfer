# LANFileTransfer for Android

An Android client compatible with [gustavo-eiji/LANFileTransfer](https://github.com/gustavo-eiji/LANFileTransfer).
Supports sending files phone → PC and receiving files PC → phone, over the same
LAN, using the same TCP protocol and mDNS discovery as the Python/Tkinter app.
Android-to-Android transfer is intentionally not implemented (per your request).

## How it was built

This was written by reading the actual PC source (not just PROTOCOL.md, which
is slightly out of date — it says the JSON key is `message_type`; the real
code uses `type`). The Android side matches `protocol.py`, `transfer.py`,
`discovery.py`, `settings.py`, and `config.py` line-for-line where it matters:

- **Transport**: TCP port `50007`. Every control message is a 4-byte
  big-endian length prefix + UTF-8 JSON `{"magic","version","type","payload"}`.
  File bytes stream raw right after `FILE_ACCEPT`, exactly `filesize` bytes.
- **Discovery**: Android `NsdManager` (mDNS/DNS-SD) advertising/browsing
  `_lanfiletransfer._tcp.` with TXT records `device_id`, `os`, `version`,
  `hostname` — the same fields `discovery.py` reads.
- **Auth**: HMAC-SHA256(security_key, nonce), same as `transfer.py`.
  `security_key` is `PBKDF2-HMAC-SHA256(password, salt, 200_000 iters)`,
  same as `config.py`.

## No PC-side changes needed

`config.py` is untouched — it still generates a fresh **random** 16-byte salt
every time you set a password via `set_new_code()`, and stores it locally in
`config/config.json` as `security_salt`. That's the right call: a fixed,
public salt would let an attacker precompute PBKDF2 tables against your
specific key ahead of time, which is exactly what a random salt is meant to
prevent.

Because the salt never travels over the network (by design — the wire
protocol has no field for it), the Android app can't infer it automatically.
Instead, the app has a **Salt (hex)** field on its settings screen: you copy
the `security_salt` value straight out of the PC's `config/config.json` and
paste it in, alongside the same password.

**Important:** every time you set a *new* password on the PC (`set_new_code`
generates a brand-new random salt each time, not just on first setup), the
salt changes too. If you ever change the PC's password, you'll need to
re-copy the new salt into the Android app as well — an old salt with a new
password will authenticate as garbage and every transfer will be rejected.

If you leave both the password and salt fields empty on the phone (matching
an unconfigured PC that's never called `set_new_code`), no PBKDF2 derivation
happens at all — useful for quick local testing before wiring up a real
password.

## Opening the project

1. On the PC, set a password through the app's UI as usual (or leave it
   unset for now).
2. Open `config/config.json` next to the PC executable/script in a text
   editor and copy the `security_salt` value (a long hex string).
3. Open the `LANFileTransferAndroid/` folder in Android Studio (Koala or
   newer). Let it sync Gradle — it will generate the wrapper jar itself, or
   you can run `gradle wrapper` first if you have Gradle installed locally.
4. Build & run on a real device on the same Wi-Fi network as the PC (mDNS
   generally doesn't work reliably from emulators — use a physical phone).
5. In the app: enter the same password as the PC, paste the salt hex you
   copied from `config.json`, tap Save. Wait for the PC to appear in the
   device list, select it, tap "Send file to selected device" to send.
   Files sent from the PC to the phone land in `Downloads/LANFileTransfer/`
   on the phone automatically — the app runs a foreground "listening"
   service for this.

## Known limitations (mirrors the PC app's own WIP status)

- No transfer cancellation, no progress persistence across app kill.
- Single transfer at a time per connection (matches the PC).
- No configurable destination folder on Android (fixed to
  `Downloads/LANFileTransfer/`).
- Minimal error handling/retry logic, same spirit as the PC's current Alpha
  status.
- mDNS (NSD) can be flaky on some Android OEM skins with aggressive
  battery/Wi-Fi optimization; if discovery doesn't find the PC, try
  disabling battery optimization for the app and confirm the PC's firewall
  allows local network connections.
