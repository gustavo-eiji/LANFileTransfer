from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo
import socket
import platform
from device import Device
from devicemanager import DeviceManager
from settings import APP_VERSION, APP_NAME, DISCOVERY_SERVICE

class MyListener(ServiceListener):

    def __init__(self, device_manager: DeviceManager) -> None:
        self.device_manager = device_manager

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")
        self.device_manager.remove_device(name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info: ServiceInfo | None = zc.get_service_info(type_, name)

        if info is None:
            return

        print(f"Service {name} added")

        properties: dict[str, str | None] = {}

        for key, value in info.properties.items():
            properties[key.decode()] = (value.decode() if value is not None else None)

        # Data validation, Device object expects str values
        remote_device_id = properties.get("device_id")
        hostname = properties.get("hostname")
        operating_system = properties.get("os")
        version = properties.get("version")


        if (hostname is None
            or operating_system is None
            or version is None
            or info.port is None
            or remote_device_id is None):

            return


        # device object is passed onwards to devicemanager.py
        device = Device(
            device_id=remote_device_id,
            hostname=hostname,
            ip_address=info.parsed_addresses()[0],
            port=info.port,
            operating_system=operating_system,
            version=version,
        )
        self.device_manager.add_device(service_name=name,device=device)

        print(self.device_manager.devices)



def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Does not actually establish a connection, used only to find local interface
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]

    except OSError:
        return '127.0.0.1'

    finally:
        s.close()


def get_operating_system() -> str:
    current_os = platform.system()

    if current_os == "Windows":
        return "Windows"
    elif current_os == "Linux":
        return "Linux"
    elif current_os == "Darwin":
        return "macOS"
    else:
        return f"Running on an unknown OS: {current_os}"


class Discovery:

    def __init__(self, device_manager: DeviceManager, device_id: str, transfer_port: int):
        self.zeroconf = Zeroconf()
        self.device_manager = device_manager
        self.device_id = device_id
        self.listener = MyListener(device_manager)
        self.ip_address = get_local_ip()
        self.hostname = f"{socket.gethostname()}[{get_operating_system()}]"

        self.properties: dict[bytes, bytes] = {
            b"device_id": device_id.encode(),
            b"os": get_operating_system().encode(),
            b"version": APP_VERSION.encode(),
            b"hostname": socket.gethostname().encode()
            }

        # Note that zeroconf does accept IP as a string, but socket.inet_aton() converts it into
        # byte format in order to comply with the official documentation
        self.service_info: ServiceInfo = ServiceInfo(type_=DISCOVERY_SERVICE,
                                   name= f"{self.hostname}.{APP_NAME}.{DISCOVERY_SERVICE}",
                                   addresses=[socket.inet_aton(self.ip_address)],
                                   port=transfer_port,
                                   properties=self.properties
                                   )

        self.browser = None


    def start(self):

        self.browser = ServiceBrowser(self.zeroconf,
                                      DISCOVERY_SERVICE,
                                      self.listener
                                      )

        self.zeroconf.register_service(self.service_info)

    def stop(self):
        self.zeroconf.unregister_service(self.service_info)

        self.zeroconf.close()