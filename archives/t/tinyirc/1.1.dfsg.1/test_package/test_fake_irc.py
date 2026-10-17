"""Bounded native smoke test for tinyirc against a loopback IRC stub."""

import os
import socket
import subprocess
import sys


def receive_until(connection, markers):
    data = b""
    while not all(marker in data for marker in markers):
        try:
            chunk = connection.recv(4096)
        except socket.timeout as exc:
            raise AssertionError(
                f"timeout waiting for {markers!r}; received {data!r}"
            ) from exc
        if not chunk:
            raise AssertionError(f"client closed before {markers!r}: {data!r}")
        data += chunk
        if len(data) > 16384:
            raise AssertionError("unexpectedly large IRC handshake")
    return data


def main():
    binary = sys.argv[1]
    terminfo = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("TERMINFO")
    if not terminfo:
        raise AssertionError("TERMINFO is required for the ncurses termcap database")
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(8)
    port = listener.getsockname()[1]
    env = os.environ.copy()
    env.update(TERM="vt100", TERMINFO=terminfo, IRCSERVER=f"127.0.0.1:{port}")
    client = subprocess.Popen(
        [binary, "tinytest", "-dumb"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        connection, _ = listener.accept()
        with connection:
            connection.settimeout(8)
            handshake = receive_until(connection, (b"USER ", b"NICK :tinytest"))
            connection.sendall(b"PING :ohos-probe\r\n")
            pong = receive_until(connection, (b"PONG :ohos-probe",))
            connection.sendall(
                b":other!ident@host PRIVMSG tinytest :hello-from-server\r\n"
            )
            client.stdin.write(b"/msg other hello-from-client\n")
            client.stdin.flush()
            outbound = receive_until(
                connection, (b"PRIVMSG other hello-from-client",)
            )
            client.stdin.write(b"/quit\n")
            client.stdin.flush()
            quit_line = receive_until(connection, (b"QUIT",))
        stdout, stderr = client.communicate(timeout=8)
        if client.returncode != 0:
            raise AssertionError(
                f"client exit {client.returncode}; stderr={stderr!r}; stdout={stdout!r}"
            )
        if b"hello-from-server" not in stdout:
            raise AssertionError(f"incoming PRIVMSG not shown: {stdout!r}")
        print(f"handshake={handshake!r}")
        print(f"pong={pong!r}")
        print(f"outbound={outbound!r}")
        print(f"quit={quit_line!r}")
        print("PASS: native IRC handshake, PING/PONG and PRIVMSG")
    finally:
        listener.close()
        if client.poll() is None:
            client.kill()
            client.communicate(timeout=2)


if __name__ == "__main__":
    main()
