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
**Note:** JSON is only used for control messages (offers, accept/reject, errors). File contents are transmitted as raw binary data for better performance.


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
    "message_type": "...",
    "payload": {}
}
```

## magic

Constant protocol identifier.

```
LANFILETRANSFER
```

Used to reject connections from unrelated software.

---

## version

Current protocol version.

```
1
```

Connections using unsupported versions should be rejected.

---

## message_type

Defines the purpose of the message.

---

# Message Types

## FILE_OFFER

Sent by sender.

Example:

```json
{
    "message_type": "FILE_OFFER",
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

---

## FILE_ACCEPT

Receiver accepts transfer.

```json
{
    "message_type":"FILE_ACCEPT",
    "payload":{}
}
```

---

## FILE_REJECT

Receiver rejects transfer.

```json
{
    "message_type":"FILE_REJECT",
    "payload":
    {
        "reason":"Authentication failed"
    }
}
```

---

# Authentication

Authentication uses a shared secret.

The sender:

1. Generates a random nonce.
2. Computes an HMAC using the shared secret and the nonce.
3. Sends both values to the receiver.

The receiver computes the expected HMAC locally using its own secret.

If the values differ:

- reject transfer
- close connection

The shared secret is never transmitted over the network.

### Why not send the password?

Sending the password directly would allow anyone monitoring the network to steal it. HMAC proves that both computers know the password without revealing it.

---

# File Transfer

After FILE_ACCEPT:

The sender streams the raw file bytes.

No JSON packets are exchanged during streaming.

Exactly `filesize` bytes are sent.

---

# Integrity Verification

Before sending a file, the sender computes its SHA-256 hash.

After receiving the file, the receiver computes the hash again.

If both hashes are identical, the transfer completed without corruption.

### Why is this necessary?

Although TCP already detects transmission errors, the hash provides an additional end-to-end integrity check and helps detect incomplete transfers or corrupted files.

---

# Connection Flow

```
┌──────────────┐                               ┌──────────────┐
│    Sender    │                               │   Receiver   │
└──────┬───────┘                               └──────┬───────┘
       │                                              │
       │──────────── TCP Connection ─────────────────>│
       │                                              │
       │ FILE_OFFER                                   │
       │ • filename                                   │
       │ • filesize                                   │
       │ • SHA-256                                    │
       │ • nonce                                      │
       │ • HMAC                                       │
       │─────────────────────────────────────────────>│
       │                                              │
       │                              Verify protocol │
       │                              Verify version  │
       │                              Verify HMAC     │
       │                                              │
       │<──────── FILE_ACCEPT / FILE_REJECT ──────────│
       │                                              │
       │========== Raw File Data (TCP Stream) =======>│
       │                                              │
       │                           Compute SHA-256    │
       │                           Compare hashes     │
       │                                              │
       │<──────────── Connection Closed ──────────────│

```

---

# Errors

Possible rejection reasons:

- Authentication failed
- Unsupported protocol version
- Invalid protocol identifier
- Timeout
- Connection lost
- Integrity verification failed

---

# Compatibility

Version 1 guarantees compatibility between:

- Windows
- macOS
- Linux (future)
- Android (future)

Implementations should reject unsupported protocol versions.