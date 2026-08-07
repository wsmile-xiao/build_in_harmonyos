#!/usr/bin/env python3
"""Exercise UDPcast CLI boundaries and a real loopback transfer."""

import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time


def run_command(command, timeout=10):
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
    )


def require_failure(command, expected):
    result = run_command(command)
    if result.returncode == 0:
        raise RuntimeError(f"command unexpectedly succeeded: {command!r}")
    if expected not in result.stdout:
        raise RuntimeError(
            f"missing {expected!r} in output from {command!r}:\n{result.stdout}"
        )
    return result.stdout


def find_even_port():
    start = 20000 + (os.getpid() % 10000) * 2
    start = min(start, 55000)
    for port in range(start - start % 2, 60000, 2):
        sockets = []
        try:
            for candidate in (port, port + 1):
                handle = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                handle.bind(("127.0.0.1", candidate))
                sockets.append(handle)
            return port
        except OSError:
            pass
        finally:
            for handle in sockets:
                handle.close()
    raise RuntimeError("no free consecutive UDP ports found")


def stop_process_group(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)


def run_loopback(sender, receiver, work):
    source = work / "source.bin"
    destination = work / "destination.bin"
    receiver_log = work / "receiver.log"
    source.write_bytes(bytes((index * 17 + 29) % 256 for index in range(65536)))
    port = find_even_port()

    common = [
        "--interface",
        "lo",
        "--portbase",
        str(port),
        "--mcast-rdv-address",
        "127.0.0.1",
        "--nokbd",
        "--no-progress",
    ]
    receiver_command = [
        receiver,
        "--file",
        str(destination),
        "--exit-wait",
        "100",
        *common,
    ]
    sender_command = [
        sender,
        "--file",
        str(source),
        "--pointopoint",
        "--min-receivers",
        "1",
        "--max-wait",
        "5",
        "--fec",
        "4x2/64",
        *common,
    ]

    with receiver_log.open("w", encoding="utf-8") as log:
        receiver_process = subprocess.Popen(
            receiver_command,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        try:
            time.sleep(0.5)
            sender_result = run_command(sender_command, timeout=30)
            if sender_result.returncode != 0:
                raise RuntimeError(f"udp-sender failed:\n{sender_result.stdout}")
            try:
                receiver_status = receiver_process.wait(timeout=30)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError("udp-receiver timed out") from error
            if receiver_status != 0:
                log.flush()
                raise RuntimeError(
                    "udp-receiver failed:\n" + receiver_log.read_text(errors="replace")
                )
        finally:
            stop_process_group(receiver_process)

    if not destination.is_file():
        raise RuntimeError("udp-receiver did not create the destination file")
    if source.read_bytes() != destination.read_bytes():
        raise RuntimeError("loopback transfer changed the input bytes")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_udpcast.py <udp-sender> <udp-receiver>")
    sender, receiver = sys.argv[1:]

    sender_usage = require_failure([sender, "--invalid-option"], "--file file")
    if "--fec" not in sender_usage:
        raise RuntimeError("udp-sender was built without FEC option support")
    require_failure([receiver, "--invalid-option"], "--file file")
    require_failure([sender, "--blocksize", "0"], "block size too small")
    require_failure(
        [receiver, "--interface", "udpcast-no-such-interface"],
        "No suitable network interface found",
    )

    root = Path(os.environ.get("TMPDIR") or os.getcwd())
    work = root / f"udpcast-conan-test-{os.getpid()}"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    try:
        run_loopback(sender, receiver, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("UDPcast command and loopback transfer tests passed")


if __name__ == "__main__":
    main()
