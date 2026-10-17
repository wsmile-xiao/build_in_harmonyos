"""Inspect complete WOL UDP datagrams on target loopback only."""

import pathlib
import socket
import subprocess
import sys


binary = pathlib.Path(sys.argv[1])
assert binary.is_file()
mac = bytes.fromhex("001122334455")
expected = b"\xff" * 6 + mac * 16


def receive(extra_args, expected_payload):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.settimeout(5)
        port = listener.getsockname()[1]
        result = subprocess.run(
            [str(binary), "--ipaddr=127.0.0.1", "--port=" + str(port)]
            + extra_args + ["00:11:22:33:44:55"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        packet, address = listener.recvfrom(2048)
        assert address[0] == "127.0.0.1", address
        assert packet == expected_payload, (len(packet), packet.hex())


receive([], expected)
receive(["--passwd=01-02-03-04-05-06"], expected + bytes.fromhex("010203040506"))
print("WOL normal and SecureON loopback UDP payloads: PASS")
