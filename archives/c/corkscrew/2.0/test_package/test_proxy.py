"""Exercise corkscrew against a deterministic local HTTP CONNECT proxy."""

import queue
import shutil
import socket
import subprocess
import threading


CLIENT_PAYLOAD = b"client-through-corkscrew\n"
PROXY_PAYLOAD = b"proxy-through-corkscrew\n"
TARGET_HOST = "target.example"
TARGET_PORT = "22"


def serve_proxy(listener, result_queue):
    try:
        conn, _ = listener.accept()
        with conn:
            conn.settimeout(10)
            request = b""
            while b"\n\n" not in request and b"\r\n\r\n" not in request:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                request += chunk

            conn.sendall(b"HTTP/1.0 200 Connection established\r\n\r\n")
            conn.sendall(PROXY_PAYLOAD)

            relayed = b""
            while len(relayed) < len(CLIENT_PAYLOAD):
                chunk = conn.recv(4096)
                if not chunk:
                    break
                relayed += chunk

            result_queue.put((request, relayed, None))
    except Exception as exc:  # Propagate proxy-thread failures to the test process.
        result_queue.put((b"", b"", exc))


def main():
    executable = shutil.which("corkscrew")
    if executable is None:
        raise AssertionError("packaged corkscrew executable is not on PATH")

    result_queue = queue.Queue()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        proxy_port = str(listener.getsockname()[1])

        thread = threading.Thread(
            target=serve_proxy, args=(listener, result_queue), daemon=True
        )
        thread.start()
        process = subprocess.run(
            [executable, "127.0.0.1", proxy_port, TARGET_HOST, TARGET_PORT],
            input=CLIENT_PAYLOAD,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        thread.join(timeout=15)

    if thread.is_alive():
        raise AssertionError("local proxy did not complete")
    request, relayed, proxy_error = result_queue.get_nowait()
    if proxy_error is not None:
        raise proxy_error
    if process.returncode != 0:
        raise AssertionError(process.stderr.decode(errors="replace"))
    if f"CONNECT {TARGET_HOST}:{TARGET_PORT} HTTP/1.0".encode() not in request:
        raise AssertionError(f"unexpected CONNECT request: {request!r}")
    if PROXY_PAYLOAD not in process.stdout:
        raise AssertionError(f"proxy payload was not relayed: {process.stdout!r}")
    if CLIENT_PAYLOAD not in relayed:
        raise AssertionError(f"client payload was not relayed: {relayed!r}")

    print("corkscrew CONNECT tunnel relayed data in both directions")


if __name__ == "__main__":
    main()
