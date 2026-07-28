from devicemanager import DeviceManager
from discovery import Discovery
import uuid
import threading

from gui import MainWindow
from transfer import TransferServer, TransferClient

import sys
from logger import Logger

logger = Logger()
sys.stdout = logger


def main():
    transfer_server = TransferServer(port=50007)

    # Generates unique ID
    device_id = str(uuid.uuid4())

    device_manager = DeviceManager()

    discovery = Discovery(device_manager, device_id, transfer_port=50007)

    transfer_client = TransferClient()

    gui = MainWindow(
        device_manager=device_manager,
        discovery=discovery,
        transfer_server=transfer_server,
        transfer_client=transfer_client,
    )




    try:
        # Advertises this computer to the network
        # Initiates listening for other computers (Zeroconf)
        discovery.start()

        server_thread = threading.Thread(
            target=transfer_server.start,
            daemon=True
        )

        server_thread.start()
        print(server_thread.is_alive())

        gui.run()

        #input("\nPress Enter to exit...\n")

    finally:
        transfer_server.stop()
        discovery.stop()

if __name__ == "__main__":
    main()
