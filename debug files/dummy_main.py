from devicemanager import DeviceManager
from discovery import Discovery
from gui import MainWindow
from transfer import TransferServer, TransferClient

import threading
import uuid
import socket


def main():

    device_id = str(uuid.uuid4())

    device_manager = DeviceManager()

    transfer_server = TransferServer(port=50008)

    discovery = Discovery(
        device_manager,
        device_id,
        transfer_server.port,
    )

    # Give this instance a different advertised name
    discovery.hostname = f"{socket.gethostname()}-Dummy[Windows]"
    discovery.service_info.name = (
        f"{discovery.hostname}._lanfiletransfer._tcp.local."
    )

    transfer_client = TransferClient()

    gui = MainWindow(
        device_manager=device_manager,
        discovery=discovery,
        transfer_server=transfer_server,
        transfer_client=transfer_client,
    )

    try:
        discovery.start()

        server_thread = threading.Thread(
            target=transfer_server.start,
            daemon=True,
        )
        server_thread.start()

        print(server_thread.is_alive())

        gui.run()

    finally:
        transfer_server.stop()
        discovery.stop()


if __name__ == "__main__":
    main()