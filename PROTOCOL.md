# LANFileTransfer Protocol

Version: 1

This document describes the network protocol used by LANFileTransfer.

The protocol is platform-independent. Any implementation (Python, Kotlin, Swift, C#, Rust, etc.) can communicate with another implementation as long as this specification is followed.

---
# About this document

This document describes the communication protocol used by LANFileTransfer.

It is intended to be simple enough that another developer can implement a compatible client in any programming language (Python, Kotlin, Swift, Rust, C#, etc.) without reading the original source code.


---

# Transport

Protocol:
- TCP

Default Port:
- 50007

Encoding:
- UTF-8 JSON packets
- Binary stream for file contents

---

# Packet Format

Every packet begins with a 4-byte unsigned integer in network byte order.

```
+-----------------+
| Length (4 bytes)|
+-----------------+
| JSON Payload    |
+-----------------+
```
**Note:** JSON is only used for control messages (offers, accept/reject, errors). File contents are transmitted as raw binary data immediately after FILE_ACCEPT for better performance.


### Why is this necessary?

TCP is a byte stream, not a message-based protocol. If two JSON messages are sent back-to-back, the operating system may deliver them together or split them across multiple reads.

By sending the message length first, the receiver knows exactly how many bytes belong to the next message.

---

# Common JSON Fields

Every message contains:

```json
{
    "magic": "LANFILETRANSFER",
    "version": 1,
    "type": "...",
    "payload": {}
}
```
---

## magic

Constant protocol identifier.

```
LANFILETRANSFER
```

Used to reject connections from unrelated software. If magic doesn't match, the connection is closed with no reply sent. See "Errors" below.

---

## version

Current protocol version.

```
1
```

Connections using unsupported versions should be rejected.

---

## type

The field naming the message's purpose is `type`. On the Python side, the ``Message`` dataclass's own attribute for this is named ``message_type`` (``Message(message_type=MessageType.FILE_OFFER, ...``), ``message.message_type == MessageType.FILE_OFFER``), that's just the local Python variable name, though, what actually goes out on the wire, and what any other-language implementation needs to read/write, is the JSON key ``type``.

---

## Payload

Every message MUST contain a `payload` JSON object. `decode_message` reads data["type"] and data["payload"] as required keys (not ``.get()`` with a default), a message missing either will raise a ``KeyError`` while decoding rather than being handled gracefully. See "Robustness notes" below.

Messages without message-specific data use:

```json
"payload": {}
```

# Message Types

## FILE_OFFER

Sent by sender to propose a file transfer.

Example:

```json
{
    "type": "FILE_OFFER",
    "payload":
    {
        "filename":"photo.jpg",
        "filesize":5312454,
        "sha256":"...",
        "nonce":"...",
        "hmac":"..."
    }
}
```

| Field    | Type    | Description |
|----------|---------|--------------|
| filename | string  | Base filename. The receiver strips any path components before saving. |
| filesize | integer | Exact size of the file in bytes. |
| sha256   | string  | Lowercase hex SHA-256 digest of the file contents. |
| nonce    | string  | Random value used for authentication (see below). |
| hmac     | string  | Lowercase hex HMAC-SHA256 proof, computed from `nonce` (see below). |

If `nonce` or `hmac` is missing, the receiver responds `FILE_REJECT` with
reason `"Client uses incompatible protocol"` instead of attempting
authentication.
---

## FILE_ACCEPT

Receiver accepts transfer.

```json
{
    "type":"FILE_ACCEPT",
    "payload":{}
}
```

---

## FILE_REJECT

Receiver rejects transfer.

```json
{
    "type":"FILE_REJECT",
    "payload":
    {
        "reason":"Authentication failed"
    }
}
```

---

# Authentication

Authentication uses a shared secret (a password), converted into a symmetric key that both devices must already know..

## Deriving the key from a password

The password is **not** used directly as the HMAC key. `config.py` first
runs it through PBKDF2:

```
security_key = PBKDF2-HMAC-SHA256(password, salt, iterations=200_000, key_length=256 bits)
```

- Salt: 16 random bytes, generated fresh **every time a password is set**
  (not just once per install). Stored only in the local `config.json` -
  it is **never transmitted over the network**, by design: a fixed or
  shared salt would let an attacker precompute PBKDF2 tables against a
  known target ahead of time, which is exactly what a random salt
  prevents.
- If no password has ever been set, `security_key` is the empty byte
  string, and PBKDF2 is not invoked.

**Consequence for other implementations:** because the salt never travels
over the wire, a second, independently-configured client cannot derive a
matching key from the password alone. Any compatible implementation needs
to obtain the current salt through some channel outside this protocol,
this document deliberately doesn't prescribe one, since it's an
application-level pairing concern, not a wire-protocol one. Whatever
mechanism is used, be aware the salt changes every time either side's
password changes, so re-pairing is needed after that.

## Per-transfer proof

For each `FILE_OFFER`, the sender:

1. Generates a random 16-byte nonce, hex-encoded (`secrets.token_hex(16)`
   in Python — 32 hex characters).
2. Computes `hmac = HMAC-SHA256(security_key, nonce_utf8_bytes)`, hex-encoded.
3. Sends both `nonce` and `hmac` in the `FILE_OFFER` payload.

The receiver computes the expected HMAC locally from its own
`security_key` and the received `nonce`, and compares in constant time
(`hmac.compare_digest` in Python; use an equivalent constant-time compare
in any other language — a naive `==` string comparison leaks timing
information).

If they don't match: send `FILE_REJECT` with reason `"Authentication
failed"`, close the connection.

The shared secret and derived key are never transmitted — only the nonce
and the resulting proof are, and a captured proof can't be replayed
against a future transfer since each one uses a fresh nonce.

---

# File Transfer

After the receiver sends `FILE_ACCEPT`, the sender streams the raw file
bytes over the same connection — no JSON framing, exactly `filesize`
bytes. One TCP connection carries exactly one offer → one
accept/reject → (if accepted) one file stream, then the connection
closes.

---

# Integrity Verification

The sender computes a SHA-256 hash of the file (streamed, 1 MiB chunks)
and includes it as `sha256` in the offer. The receiver computes its own
hash of what it received and compares.

**This check happens entirely on the receiving side, after the full file
has already been transferred, and the result is never reported back to
the sender over the wire.** If the hashes don't match, the receiver
deletes the file locally and returns a local failure indication to its own
caller, the sender has no protocol-level way to learn a mismatch
occurred; from the sender's point of view, as far as the wire protocol is
concerned, the transfer completed normally.

---

# Discovery

Devices find each other via mDNS/DNS-SD (`discovery.py`, using the
`zeroconf` library), not via any message defined above.

- **Service type**: `_lanfiletransfer._tcp.local.`
- **Advertised port**: the TCP transfer port (default 50007).
- **TXT record fields**: `device_id`, `os`, `version`, `hostname`.

A resolved service missing any of these fields, or without a usable port,
is ignored by the reference implementation.

---

# Message loop

Inside `handle_client`, the server reads one message at a time in a loop:

Inside `handle_client`, the server reads one message at a time in a loop.
**`FILE_OFFER` is the only message type this server accepts.** It's
handled entirely inline — authentication, `FILE_ACCEPT`/`FILE_REJECT`,
then `receive_file()` if accepted — and the loop `break`s afterward,
ending the connection. This is the only path described under
"Authentication" and "File Transfer" above.

Any other message type (including the enum's `PING`, `PONG`, `TEXT`, and
`ERROR` values, or a client sending `FILE_ACCEPT`/`FILE_REJECT`
unprompted) is logged and the connection is closed — the same way a bad
`magic`/`version` is already handled, with no reply sent back.

An earlier version of this server routed anything that wasn't
`FILE_OFFER` through a `dispatch_message()` function
(`dispatcher.py`), which handled `TEXT`/`PING` and had two problems: it
defined a second, unauthenticated `FILE_OFFER` handler that only
happened not to run because of the specific order of the check in
`handle_client` (a fragile guarantee, not a real one), and it raised an
uncaught `ValueError` for any message type it didn't recognize, which,
since `accept_connections()` handles clients synchronously with no
per-connection threading, could have taken down the entire listening
server, not just the one connection. `TEXT`/`PING` were unused and
unwired to any UI feature, so `dispatch_message()` and `dispatcher.py`
were removed entirely rather than patched, eliminating both problems at
once instead of hardening a code path nothing actually needed.

---

# Errors

## Sent as FILE_REJECT (the peer gets an explicit message)

- `"Client uses incompatible protocol"` — `nonce`/`hmac` missing from the offer
- `"Authentication failed"` — HMAC didn't match

## Not sent as any message — connection just closes

- Invalid `magic`
- Unsupported `version`
- Socket timeout (30 seconds by default)
- Connection lost mid-transfer

## Never communicated over the wire at all

- SHA-256 mismatch after a full transfer (receiver-local only — see
  "Integrity Verification" above)

The previous version of this document listed all of the above as one
undifferentiated list of "possible rejection reasons," which reads as if
every case results in a `FILE_REJECT` message. Only the first two do.

## Robustness notes

- `decode_message` uses required-key indexing (`data["type"]`,
  `data["payload"]`) rather than `.get()` with defaults, unlike `magic`
  and `version` which use `.get()`. A JSON control message missing
  either key raises `KeyError`, not the `ValueError` that
  `receive_packet`'s `except ValueError` clause is written to catch —
  so a malformed message shaped that way isn't handled by the existing
  error handling.
- See "Message loop" above for the same category of issue with
  `dispatch_message`'s unhandled `ValueError` on unexpected message
  types.

---

# Compatibility

This repository's own implementation targets Windows and macOS
(Python/Tkinter). A separately maintained Android client exists and
interoperates with this wire protocol as of version 1 — but genuine
cross-implementation compatibility depends on solving the salt-sharing
problem described under "Authentication," which is outside what this
protocol alone guarantees. Implementations should reject unsupported
protocol versions per the rules above.
