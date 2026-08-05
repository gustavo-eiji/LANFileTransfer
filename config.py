from pathlib import Path
import json
import sys
import hashlib
import secrets

# PATCH FOR ANDROID INTEROP
# FIXED_SALT = bytes.fromhex("3f2a9c8e1d4b7f605a3c9e1b4d7f2a06")

if getattr(sys, "frozen", False):
    # Running as a bundled executable
    base_dir = Path(sys.executable).parent
else:
    # Running as a Python script
    base_dir = Path(__file__).resolve().parent

def derive_key(password:str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        200_000)


class Config:
    def __init__(self):

        self.folder = base_dir / "config"
        self.folder.mkdir(exist_ok=True)

        self.file = self.folder / "config.json"

        self.security_key = ""
        self.security_salt = ""
        self.transfer_port = 50007

        self.load()

    def load(self):
        if not self.file.exists():
            self.save()
            return

        data = json.loads(self.file.read_text())

        self.security_key = data.get("security_key", "")
        self.security_salt = data.get("security_salt", "")
        self.transfer_port = data.get("transfer_port", 50007)

    def save(self):
        self.file.write_text(
            json.dumps(
                {
                    "security_key": self.security_key,
                    "security_salt": self.security_salt,
                    "transfer_port": self.transfer_port,
                },
                indent=4,
            )
        )

    def set_new_code(self, new_code: str):

        salt = secrets.token_bytes(16)

        key = derive_key(new_code, salt)

        self.security_key = key.hex()
        self.security_salt = salt.hex()

        self.save()

    def set_new_transfer_port(self, new_transfer_port: int):
        self.transfer_port = new_transfer_port
        self.save()

    def get_security_key(self) -> bytes:
        return bytes.fromhex(self.security_key)
