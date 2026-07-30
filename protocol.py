from dataclasses import dataclass
from enum import Enum
import json
from typing import Any
from settings import PROTOCOL_MAGIC, PROTOCOL_VERSION


class MessageType(Enum):
    PING = "PING"
    PONG = "PONG"
    TEXT = "TEXT"

    FILE_OFFER = "FILE_OFFER"
    FILE_ACCEPT = "FILE_ACCEPT"
    FILE_REJECT = "FILE_REJECT"

    ERROR = "ERROR"

@dataclass
class Message:
    message_type: MessageType
    payload: dict[str, Any] | None = None

def encode_message(message: Message) -> bytes:
    # Serialize a Message object into UTF-8 encoded JSON bytes.
    data = {
        "magic": PROTOCOL_MAGIC,
        "version": PROTOCOL_VERSION,
        "type": message.message_type.value,
        "payload": message.payload,
    }

    return json.dumps(data).encode("utf-8")

def decode_message(raw_data: bytes) -> Message:
    # Deserialize UTF-8 encoded JSON bytes into a Message object.
    data = json.loads(raw_data.decode("utf-8"))

    if data.get("magic") != PROTOCOL_MAGIC:
        raise ValueError("Invalid protocol identifier.")

    if data.get("version") != PROTOCOL_VERSION:
        raise ValueError(f"Invalid protocol version: {data.get('version')}")

    return Message(
        message_type=MessageType(data["type"]),
        payload=data["payload"],
    )