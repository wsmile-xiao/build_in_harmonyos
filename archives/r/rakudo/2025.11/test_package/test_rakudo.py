#!/usr/bin/env python3
"""Run packaged Rakudo and assert real Raku language behavior."""

import logging
import os
import subprocess
import sys


raku, script = sys.argv[1:]
package = os.path.dirname(os.path.dirname(raku))

assert os.environ.get("MVM_JIT_DISABLE") == "1", "MVM JIT must be disabled on OHOS"
assert not os.path.exists(os.path.join(package, "include")), "application package contains headers"
assert not os.path.exists(os.path.join(package, "share", "pkgconfig")), (
    "application package contains pkg-config development metadata"
)
package_files = [
    name
    for _, _, names in os.walk(package)
    for name in names
]
assert not any(
    marker in name
    for name in package_files
    for marker in ("-debug", "-gdb", "-lldb", "-valgrind")
), "application package contains development helper files"

version = subprocess.run([raku, "--version"], check=True, text=True, capture_output=True)
assert "2025.11" in version.stdout, version.stdout

result = subprocess.run([raku, script], check=True, text=True, capture_output=True)
actual = result.stdout.splitlines()
expected = [
    "qos-sum=3",
    "topic=sensors/temp",
    "retain=yes",
    "utf8-bytes=8",
    "utf8-roundtrip=MQTT ✓",
    "class=events:2",
    "raku-smoke=ok",
]
assert actual == expected, f"unexpected Raku output: {actual!r}"
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.info("Rakudo consumer checks passed: 4 package checks + version + 7 outputs")
