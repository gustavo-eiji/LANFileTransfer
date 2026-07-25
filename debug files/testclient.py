from transfer import TransferClient
from protocol import Message, MessageType

HOST = "127.0.0.1"
PORT = 50007

client = TransferClient()

client.send_file(
    path=r"C:\Users\get21\Pictures\Wallpapers\1743528206706.jpeg",
    host=HOST,
    port=PORT,
)