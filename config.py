from pathlib import Path
import json
import sys

if getattr(sys, "frozen", False):
    # Running as a bundled executable
    base_dir = Path(sys.executable).parent
else:
    # Running as a Python script
    base_dir = Path(__file__).resolve().parent



class Config:
    def __init__(self):

        self.folder = base_dir / "config"
        self.folder.mkdir(exist_ok=True)

        self.file = self.folder / "config.json"

        self.security_code = ""
        self.transfer_port = 50007

        self.load()

    def load(self):
        if not self.file.exists():
            self.save()
            return

        data = json.loads(self.file.read_text())

        self.security_code = data.get("security_code", "")
        self.transfer_port = data.get("transfer_port", 50007)

    def save(self):
        self.file.write_text(
            json.dumps(
                {
                    "security_code": self.security_code,
                    "transfer_port": self.transfer_port,
                },
                indent=4,
            )
        )

    def set_new_code(self, new_code: str):
        self.security_code = new_code
        self.save()

    def set_new_transfer_port(self, new_transfer_port: int):
        self.transfer_port = new_transfer_port
        self.save()
