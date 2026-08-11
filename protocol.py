from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any
from settings import PROTOCOL_MAGIC, PROTOCOL_VERSION


class MessageType(Enum):

    FILE_OFFER = "FILE_OFFER"
    FILE_ACCEPT = "FILE_ACCEPT"
    FILE_REJECT = "FILE_REJECT"


@dataclass
class Message:
    message_type: MessageType
    payload: dict[str, Any] = field(default_factory=dict) # | None = None

def encode_message(message: Message) -> bytes:
    # Serialize a Message object into UTF-8 encoded JSON bytes.
    data = {
        "magic": PROTOCOL_MAGIC,
        "version": PROTOCOL_VERSION,
        "type": message.message_type.value,
        "payload": message.payload or {},
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