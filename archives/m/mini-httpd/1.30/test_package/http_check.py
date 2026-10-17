import socket
import sys

port = int(sys.argv[1])
try:
    s = socket.create_connection(("127.0.0.1", port), timeout=4)
except OSError:
    sys.exit(2)
s.sendall(b"GET / HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
data = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    data += chunk
s.close()
sys.stdout.write(data.decode("utf-8", "replace"))
