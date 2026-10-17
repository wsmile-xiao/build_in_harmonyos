#!/usr/bin/env python3
import os
import struct
import subprocess
import sys
import tempfile


PACKAGE = sys.argv[1]
BIN = os.path.join(PACKAGE, "bin")
DATA = os.path.join(PACKAGE, "share", "p0f", "p0f.fp")


def run(name, args, expected_code=None, expected_text=None):
    path = os.path.join(BIN, name)
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        raise RuntimeError(f"missing executable: {path}")
    result = subprocess.run(
        [path, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    if expected_code is not None and result.returncode != expected_code:
        raise RuntimeError(f"{name} returned {result.returncode}: {result.stdout}")
    if expected_text and expected_text.lower() not in result.stdout.lower():
        raise RuntimeError(f"{name} output lacks {expected_text!r}: {result.stdout}")
    print(f"PASS {name} {' '.join(args) or '(no args)'}")


def make_syn_pcap(path):
    eth = bytes.fromhex("00112233445566778899aabb0800")
    ip = bytes.fromhex("4500002812344000400600000a0000010a000002")
    tcp = struct.pack(
        "!HHIIHHHH", 12345, 80, 1, 0, (5 << 12) | 0x002, 65535, 0, 0
    )
    packet = eth + ip + tcp
    with open(path, "wb") as capture:
        capture.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        capture.write(struct.pack("<IIII", 1, 0, len(packet), len(packet)))
        capture.write(packet)


with tempfile.NamedTemporaryFile(prefix="p0f-syn-", suffix=".pcap", dir=os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))) as capture:
    make_syn_pcap(capture.name)
    run("p0f", ["-f", DATA, "-r", capture.name], expected_code=0, expected_text="client")

run("p0f-client", [], expected_code=1, expected_text="usage")
run("p0f-sendsyn", [], expected_code=1, expected_text="usage")
run("p0f-sendsyn6", [], expected_code=1, expected_text="usage")
print("p0f command consumer tests passed: 4/4")
