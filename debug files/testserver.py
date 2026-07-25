from transfer import TransferServer

server = TransferServer()

try:
    server.start()
except KeyboardInterrupt:
    print("\nStopping server...")
    server.stop()